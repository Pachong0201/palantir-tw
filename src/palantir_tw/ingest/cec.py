"""中选会选举数据库导入器（证据 A 级）。

数据源：政府资料开放平台数据集 13119「選舉資料庫(含選舉區資料)」
打包文件 votedata.zip 内按 <选举>/<选区类别>/<area 类别>/ 存放 CSV：

  elbase.csv  区划代码表  (省市别,縣市別,選區別,鄉鎮市區別,村里別,名稱)
  elpaty.csv  政党代码表  (政黨代號,政黨名稱)
  elcand.csv  候选人表    (…,村里別,號次,姓名,政黨代號,性別,出生日期,年齡,出生地,學歷,現任,當選,副手)
  elctks.csv  得票表      (…,村里別,投開票所別,號次,得票數,得票率,當選註記)

縣市長层级取 選區別=00,鄉鎮市區別=000,村里別=0000,投開票所別=0000 的汇总行。
"""

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Candidacy, Entity
from ..ontology import EntityType

CEC_VOTEDATA_URL = "https://data.cec.gov.tw/選舉資料庫/votedata.zip"


@dataclass
class ImportStats:
    districts: int = 0
    parties: int = 0
    persons: int = 0
    candidacies: int = 0
    elected: int = 0
    warnings: list[str] = field(default_factory=list)


def _read_csv(path: Path) -> list[list[str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [[c.strip() for c in row] for row in csv.reader(f) if row and any(c.strip() for c in row)]


def _upsert_entity(
    session: Session,
    *,
    type_: EntityType,
    name: str,
    external_id: str,
    props: dict | None = None,
    aliases: list | None = None,
    cache: dict,
) -> tuple[Entity, bool]:
    key = (type_.value, external_id)
    if key in cache:
        return cache[key], False
    ent = session.scalar(
        select(Entity).where(Entity.type == type_.value, Entity.external_id == external_id)
    )
    if ent is not None:
        ent.name = name
        ent.props = {**(ent.props or {}), **(props or {})}
        cache[key] = ent
        return ent, False
    ent = Entity(type=type_.value, name=name, external_id=external_id, props=props or {}, aliases=aliases or [])
    session.add(ent)
    session.flush()
    cache[key] = ent
    return ent, True


def _party_name(party_code: str, parties: dict[str, str]) -> str:
    return parties.get(party_code, "無黨籍" if party_code == "999" else f"代號{party_code}")


def import_cec_office_dir(
    session: Session,
    office_dir: Path,
    election: Entity,
    office: str,
    stats: ImportStats,
    cache: dict,
) -> None:
    """导入一个选务目录（如 C1/prv、C1/city）下的縣市层级数据。"""
    elpaty = _read_csv(office_dir / "elpaty.csv")
    elbase = _read_csv(office_dir / "elbase.csv")
    elcand = _read_csv(office_dir / "elcand.csv")
    elctks = _read_csv(office_dir / "elctks.csv")

    parties = {row[0]: row[1] for row in elpaty if len(row) >= 2}

    # 县级区划：選區別=00,鄉鎮市區別=000,村里別=0000，排除全国汇总行
    districts: dict[str, Entity] = {}
    for row in elbase:
        if len(row) < 6 or row[0] == "00":
            continue
        if row[2] == "00" and row[3] == "000" and row[4] == "0000":
            prv, city, name = row[0], row[1], row[5]
            key = f"{prv}-{city}"
            ent, created = _upsert_entity(
                session,
                type_=EntityType.DISTRICT,
                name=name,
                external_id=f"cec:{key}",
                props={"level": "county", "prv_code": prv, "city_code": city},
                cache=cache,
            )
            districts[key] = ent
            stats.districts += int(created)

    # 候选人（县级汇总行：選區別=00）
    cand_rows = {}
    for row in elcand:
        if len(row) < 14 or row[2] != "00":
            continue
        prv, city, no = row[0], row[1], row[5]
        cand_rows[(f"{prv}-{city}", no)] = row

    # 得票（县级汇总行：選區別=00,鄉鎮=000,村里=0000,投開票所=0000）
    for row in elctks:
        if len(row) < 10:
            continue
        if row[2] != "00" or row[3] != "000" or row[4] != "0000" or row[5] != "0000":
            continue
        prv, city, no = row[0], row[1], row[6]
        dkey = f"{prv}-{city}"
        district = districts.get(dkey)
        cand = cand_rows.get((dkey, no))
        if district is None or cand is None:
            stats.warnings.append(f"vote row without district/candidate: {row[:7]}")
            continue

        party_code = cand[7] if len(cand) > 7 else "999"
        party = None
        if party_code != "999":
            party, created = _upsert_entity(
                session,
                type_=EntityType.PARTY,
                name=_party_name(party_code, parties),
                external_id=f"cec-party:{party_code}",
                props={"cec_code": party_code},
                cache=cache,
            )
            stats.parties += int(created)

        name = cand[6]
        birth_roc = cand[9] if len(cand) > 9 else ""
        sex = {"1": "男", "2": "女"}.get(cand[8] if len(cand) > 8 else "")
        person, created = _upsert_entity(
            session,
            type_=EntityType.PERSON,
            name=name,
            external_id=f"cec-cand:{name}:{birth_roc}",
            props={"birth_roc": birth_roc, "birthplace": cand[11] if len(cand) > 11 else ""},
            cache=cache,
        )
        stats.persons += int(created)

        votes = int(row[7]) if row[7].isdigit() else None
        vote_share = float(row[8]) if row[8] else None
        elected = "*" in row[9:] or (len(cand) > 14 and "*" in cand[14])

        exists = session.scalar(
            select(Candidacy).where(
                Candidacy.person_id == person.id,
                Candidacy.election_id == election.id,
                Candidacy.district_id == district.id,
            )
        )
        if exists is None:
            session.add(
                Candidacy(
                    person_id=person.id,
                    election_id=election.id,
                    district_id=district.id,
                    party_id=party.id if party else None,
                    office=office,
                    ballot_no=int(no),
                    votes=votes,
                    vote_share=vote_share,
                    elected=elected,
                    incumbent=cand[13] == "Y",
                    sex=sex or None,
                    birth_roc=birth_roc or None,
                    education=cand[12] if len(cand) > 12 else None,
                )
            )
            stats.candidacies += 1
            stats.elected += int(elected)


def import_cec_simple_dir(
    session: Session,
    simple_dir: Path,
    election_name: str,
    election_date: date,
    office: str,
    district_name: str,
    district_external_id: str,
    stats: ImportStats | None = None,
) -> ImportStats:
    """导入特殊格式目录（如 2022年_嘉義市長重行選舉）。

    cand.csv: 號次,名字,政黨名稱
    prof.csv: 行政區別,村里別,投開票所別,號次1…號次N,…（投票所级，需汇总）
    当选人按得票最高者计算（该格式无當選註记）。
    """
    stats = stats or ImportStats()
    cache: dict = {}

    cands = _read_csv(simple_dir / "cand.csv")
    cand_rows = [r for r in cands if r and r[0].isdigit()]

    prof = _read_csv(simple_dir / "prof.csv")
    totals = {int(r[0]): 0 for r in cand_rows}
    for row in prof[1:]:
        if len(row) < 3 + len(cand_rows):
            continue
        for i, r in enumerate(cand_rows):
            cell = row[3 + i].replace(",", "")
            totals[int(r[0])] += int(cell) if cell.isdigit() else 0

    total_votes = sum(totals.values())
    winner_no = max(totals, key=totals.get) if totals else None

    election, _ = _upsert_entity(
        session,
        type_=EntityType.ELECTION,
        name=election_name,
        external_id=f"cec-election:{simple_dir.name}",
        props={"date": election_date.isoformat(), "kind": "地方公職人員選舉"},
        cache=cache,
    )
    district, created = _upsert_entity(
        session,
        type_=EntityType.DISTRICT,
        name=district_name,
        external_id=district_external_id,
        props={"level": "county"},
        cache=cache,
    )
    stats.districts += int(created)

    party_codes = {"中國國民黨": "1", "民主進步黨": "16", "台灣民眾黨": "350", "時代力量": "267"}
    for r in cand_rows:
        no, name, party_name = r[0], r[1], r[2] if len(r) > 2 else "無"
        party = None
        if party_name and party_name != "無":
            code = party_codes.get(party_name, f"custom:{party_name}")
            party, created = _upsert_entity(
                session,
                type_=EntityType.PARTY,
                name=party_name,
                external_id=f"cec-party:{code}",
                props={"cec_code": code},
                cache=cache,
            )
            stats.parties += int(created)

        person, created = _upsert_entity(
            session,
            type_=EntityType.PERSON,
            name=name,
            external_id=f"cec-cand:{name}:{election_date.isoformat()}",
            cache=cache,
        )
        stats.persons += int(created)

        votes = totals.get(int(no))
        exists = session.scalar(
            select(Candidacy).where(
                Candidacy.person_id == person.id,
                Candidacy.election_id == election.id,
                Candidacy.district_id == district.id,
            )
        )
        if exists is None:
            session.add(
                Candidacy(
                    person_id=person.id,
                    election_id=election.id,
                    district_id=district.id,
                    party_id=party.id if party else None,
                    office=office,
                    ballot_no=int(no),
                    votes=votes,
                    vote_share=round(votes * 100 / total_votes, 2) if total_votes else None,
                    elected=int(no) == winner_no,
                )
            )
            stats.candidacies += 1
            stats.elected += int(int(no) == winner_no)

    return stats


def import_cec_election(
    session: Session,
    root: Path,
    election_dir: str,
    election_name: str,
    election_date: date,
    office_dirs: dict[str, str] | None = None,
) -> ImportStats:
    """导入一个选举场次下的所有县级首长选区。

    root: 解压后的 voteData/ 目录；election_dir: 如 '2022-111年地方公職人員選舉'
    office_dirs: {子目录名: office 标签}，默认 C1 的 prv/city → 直轄市長/縣市長
    """
    office_dirs = office_dirs or {"prv": "直轄市長", "city": "縣市長"}
    cache: dict = {}
    stats = ImportStats()

    election, _ = _upsert_entity(
        session,
        type_=EntityType.ELECTION,
        name=election_name,
        external_id=f"cec-election:{election_dir}",
        props={"date": election_date.isoformat(), "kind": "地方公職人員選舉"},
        cache=cache,
    )

    base = Path(root) / election_dir / "C1"
    for sub, office in office_dirs.items():
        office_dir = base / sub
        if office_dir.is_dir():
            import_cec_office_dir(session, office_dir, election, office, stats, cache)
        else:
            stats.warnings.append(f"missing dir: {office_dir}")

    return stats
