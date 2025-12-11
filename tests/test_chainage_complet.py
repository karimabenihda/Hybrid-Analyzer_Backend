import app.main as main
from fastapi.testclient import TestClient

client = TestClient(main.app)

def test_login(mocker):
    fake_user = mocker.Mock()
    fake_user.id = 1
    fake_user.username = "string"
    fake_user.firstname = "first"
    fake_user.lastname = "last"
    fake_user.password = "hashedpass"

    mocker.patch("app.main.pwd_context.verify", return_value=True)

    fake_db = mocker.Mock()
    fake_db.query().filter().first.return_value = fake_user
    mocker.patch("app.main.get_db", return_value=iter([fake_db]))

    response = client.post("/login", json={
        "username": "string",
        "password": "hashedpass"
    })

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "string"


# def test_register(mocker):
    
    # 1) fake user returned
    # fake_user = {
    #     "id":1,
    #     "username":"john",
    #     "firstname":"John",
    #     "lastname":"Doe"
    # }

    # # 2) fake database object
    # fake_db = mocker.Mock()

    # # user does not exist
    # fake_db.query.return_value.filter.return_value.first.return_value = None

    # # fake refresh
    # fake_db.refresh.side_effect = lambda u: None

    # # 3) mock get_db
    # mocker.patch("app.main.get_db", return_value=fake_db)

    # # 4) mock hash
    # mocker.patch("app.main.pwd_context.hash", return_value="hashed")

    # # 5) call API
    # response = client.post("/register", json={
    #     "username":"john",
    #     "firstname":"John",
    #     "lastname":"Doe",
    #     "password":"123"
    # })

    # # 6) assertion
    # assert response.status_code == 200
    
    
def test_add_category(mocker):
    fake=mocker.Mock()
    mocker.patch("app.main.get_db",return_value=fake)
    response = client.post("/categories", json={
        "name": "technology"
    })    
    assert response.status_code == 200
