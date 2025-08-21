from multiprocessing.managers import SyncManager, Namespace

class MyManager(SyncManager):
    pass

class StageNamespace(Namespace):
    stage_offset_ms = 0.0

def get_my_manager() -> SyncManager:
    manager = MyManager()
    return manager
