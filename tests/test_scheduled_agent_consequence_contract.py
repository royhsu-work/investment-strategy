YªçŠx-®éÜj×¢ëiºÚ+Š§j[h‘éÜ¢éíã¾|N‹Z–‹­¦ëeŠw¬Ôˆˆ‰á•ÕÑ…‰±”½¹Í•ÅÕ•¹”Ñ½Á½±½ä…¹¥¹Ñ•ÉÉÕÁÑ¥½¸µ‰½Õ¹‘…ÉäÉ•É•ÍÍ¥½¹Ì¸ˆˆˆ()™É½´}}™ÕÑÕÉ•}|¥µÁ½ÉÐ…¹¹½Ñ…Ñ¥½¹Ì()¥µÁ½ÉÐ©Í½¸()¥µÁ½ÉÐÁåÑ•ÍÐ()¥µÁ½ÉÐ¥¹Ù•ÍÑµ•¹Ñ}ÍÑÉ…Ñ•ä¹Í¡•‘Õ±•‘}…•¹Ñ}…ÁÁ±¥…Ñ¥½¹}‰É¥‘”…Ì‰É¥‘”)¥µÁ½ÉÐ¥¹Ù•ÍÑµ•¹Ñ}ÍÑÉ…Ñ•ä¹Í¡•‘Õ±•‘}…•¹Ñ}•™™•ÑÌ…Ì•™™•ÑÌ)™É½´¥¹Ù•ÍÑµ•¹Ñ}ÍÑÉ…Ñ•çŽyòÚ$z{-®éÜj× spec.successor_required


def test_archive_terminal_spec_names_merged_successor_evidence() -> None:
    spec = consequence_spec_for(Action.FINALIZE_ARCHIVE, ResultKind.LIFECYCLE_COMPLETE)
    assert spec.evidence_target is EvidenceTarget.MERGED_PR_HEAD
    assert spec.successor_required is False
