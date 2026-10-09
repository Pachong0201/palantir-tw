import zipfile
from datetime import date
from pathlib import Path

import typer

from .db import init_db, session_scope
from .ingest.cec import CEC_VOTEDATA_URL, import_cec_election

app = typer.Typer(help="palantir-tw: 台湾开源情报平台")


@app.command()
def initdb() -> None:
    """建表（幂等）。"""
    init_db()
    typer.echo("database initialized")


@app.command()
def import_cec(
    path: Path = typer.Argument(..., help="解压后的 voteData/ 目录（其下含各选举目录）"),
    election_dir: str = typer.Option("2022-111年地方公職人員選舉"),
    election_name: str = typer.Option("111年地方公職人員選舉"),
    election_date: str = typer.Option("2022-11-26"),
) -> None:
    """导入中选会选举数据（县级首长 C1/prv + C1/city）。"""
    init_db()
    with session_scope() as s:
        stats = import_cec_election(
            s, path, election_dir, election_name, date.fromisoformat(election_date)
        )
    typer.echo(
        f"imported: districts={stats.districts} parties={stats.parties} "
        f"persons={stats.persons} candidacies={stats.candidacies} elected={stats.elected}"
    )
    for w in stats.warnings:
        typer.echo(f"WARN {w}")


@app.command()
def fetch_cec(
    out_dir: Path = typer.Option(Path("data/cec"), help="输出目录"),
    keep_zip: bool = typer.Option(False),
) -> Path:
    """下载中选会 votedata.zip 并解压。返回 voteData/ 目录路径。"""
    import httpx

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / "votedata.zip"
    typer.echo(f"downloading {CEC_VOTEDATA_URL} ...")
    with httpx.stream("GET", CEC_VOTEDATA_URL, follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    typer.echo("extracting ...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out_dir)
    if not keep_zip:
        zip_path.unlink()
    # 包内路径：votedata/votedata/voteData/
    candidates = list(out_dir.rglob("voteData"))
    root = candidates[0] if candidates else out_dir
    typer.echo(f"voteData at {root}")
    return root


@app.command()
def seed_cec_2022(
    work_dir: Path = typer.Option(Path("data/cec"), help="下载/解压目录"),
) -> None:
    """一键：下载中选会数据包 → 导入 111 年地方公职人员选举县级首长数据。"""
    root = fetch_cec(work_dir)
    init_db()
    with session_scope() as s:
        stats = import_cec_election(
            s, root, "2022-111年地方公職人員選舉", "111年地方公職人員選舉",
            date(2022, 11, 26),
        )
        # 嘉义市长重行选举（候选人死亡延期）为独立目录、不同 CSV 格式
        rerun = root.parent / "2022年_嘉義市長重行選舉"
        if rerun.is_dir():
            from .ingest.cec import import_cec_simple_dir

            stats2 = import_cec_simple_dir(
                s, rerun, "2022年嘉義市長重行選舉", date(2022, 12, 18),
                office="縣市長", district_name="嘉義市", district_external_id="cec:10-020",
            )
            stats.districts += stats2.districts
            stats.parties += stats2.parties
            stats.persons += stats2.persons
            stats.candidacies += stats2.candidacies
            stats.elected += stats2.elected
        else:
            typer.echo("WARN 未找到嘉義市長重行選舉目录，嘉義市缺失")
    typer.echo(
        f"imported: districts={stats.districts} parties={stats.parties} "
        f"persons={stats.persons} candidacies={stats.candidacies} elected={stats.elected}"
    )


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """起 API + 工作台。"""
    import uvicorn

    uvicorn.run("palantir_tw.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
