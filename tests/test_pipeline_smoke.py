from core.annotator import EnterpriseAnnotator
from core.indexer import EnterpriseIndexer
from core.miner import EnterpriseMiner
from core.profiler import EnterpriseProfiler
from core.resolver import EnterpriseResolver
from main import UPSCImprovementEngine


def test_pipeline_core_symbols_are_importable():
    assert EnterpriseProfiler is not None
    assert EnterpriseIndexer is not None
    assert EnterpriseMiner is not None
    assert EnterpriseResolver is not None
    assert EnterpriseAnnotator is not None
    assert UPSCImprovementEngine is not None
