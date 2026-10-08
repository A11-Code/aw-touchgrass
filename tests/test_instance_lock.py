import main


def test_instance_lock_path_is_repo_local():
    assert main.INSTANCE_LOCK_PATH.parent == main.CONFIG_PATH.parent
