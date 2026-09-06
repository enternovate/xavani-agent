def test_pets_imports():
    import xavani_cli.pets as mod

    assert mod is not None


def test_pets_exposes_consumer_names():
    from xavani_cli import pets

    assert callable(pets._set_active)
    assert callable(pets._set_enabled)
    assert callable(pets.print_pet_gallery)
    assert callable(pets.set_pet_scale)
    assert callable(pets.toggle_pet_display)


def test_pet_store_imports():
    from agent.pet import store

    assert store is not None
