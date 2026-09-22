"""CiteGuard：claim 抽取 + 存在/条号/时效三检（FRAMEWORK 戒律 4、附录 D）。"""

from .check import CiteCheck, check_claim
from .extract import Claim, ClaimExtraction, extract_claims

__all__ = ["CiteCheck", "Claim", "ClaimExtraction", "check_claim", "extract_claims"]
