"""Ontology definitions: entity types, assertion predicates, evidence grades.

图谱里没有裸事实——每条关系都是带证据等级、来源与有效期的断言。
"""

from enum import Enum


class EntityType(str, Enum):
    PERSON = "person"  # 政治人物：候选人、民代、官员、幕僚、金主
    PARTY = "party"  # 政党/派系
    ORGANIZATION = "organization"  # 公司、财团法人、协会、媒体
    DISTRICT = "district"  # 行政区/选区
    ELECTION = "election"  # 选举场次
    EVENT = "event"  # 政治事件
    DOCUMENT = "document"  # 来源文档


class Predicate(str, Enum):
    RAN_IN = "参选于"  # person -> candidacy/election（结构化结果走 candidacies 表）
    MEMBER_OF = "隶属政党"  # person -> party
    FAMILY_OF = "亲属"  # person -> person
    SPOUSE_OF = "配偶"  # person -> person
    STAFF_OF = "幕僚/助理"  # person -> person
    DONATED_TO = "捐赠"  # person/org -> person（政治献金）
    INVOLVED_IN = "涉案"  # person -> event
    ENDORSED = "表态支持"  # person -> person
    RUNS = "经营/负责人"  # person -> organization
    MENTIONS = "提及"  # document -> entity


class EvidenceGrade(str, Enum):
    """证据分级（沿用 ogasawara 框架 A–E）。"""

    A = "A"  # 官方原始件（CEC 开票、监察院申报、判决书）
    B = "B"  # 官方转述或多源交叉印证
    C = "C"  # 单一可靠媒体
    D = "D"  # 社媒单一来源
    E = "E"  # 未证实线索


class AssertionStatus(str, Enum):
    ASSERTED = "asserted"  # 已确认入库
    CONTESTED = "contested"  # 存在冲突断言
    RETRACTED = "retracted"  # 已撤下
    PENDING_REVIEW = "pending_review"  # 待人工审核
