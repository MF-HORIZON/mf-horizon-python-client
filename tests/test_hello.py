import mf_horizon_client.hello as hello


def test_hello():
    name = "Bob"
    assert f"Hello, {name}!" == hello.greeting_text(name)
