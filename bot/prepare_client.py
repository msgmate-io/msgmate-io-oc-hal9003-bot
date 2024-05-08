from open_chat_api_client.models import LoginInfo, AugmentedBotUser, UserSelf
from open_chat_api_client.client import AuthenticatedClient, Client
from open_chat_api_client.api.bot import bot_login_create

def prepare_client(
    bot_username: str,
    bot_password: str,
    server_url: str
) -> tuple[AuthenticatedClient, str, str]:
    client = Client(
        base_url=server_url
    )
    res: AugmentedBotUser = bot_login_create.sync(
        client=client,
        body=LoginInfo(
            username=bot_username,
            password=bot_password
        )
    )
    print("Logged in as bot", res)
    csrftoken = res.additional_properties['csrftoken']
    sessionid = res.additional_properties['sessionid']
    auth_client = Client(
        base_url=server_url,
        headers={
            "X-CSRFToken": csrftoken,
            "Cookie": f"sessionid={sessionid}; csrftoken={csrftoken}"
        }
    )
    return auth_client, csrftoken, sessionid
