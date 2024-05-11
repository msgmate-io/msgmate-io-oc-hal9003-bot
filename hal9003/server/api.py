from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import serializers
from open_chat_api_client.api.messages import messages_send_create
from open_chat_api_client.models import SendMessage
import bot.config as bc
import requests

auth_client = None

@api_view(["GET"])
@permission_classes([])
@authentication_classes([])
def index(request):
    ip = get_client_ip(request)
    return Response({"message": "Hello, I'm Online! Hello there! Your IP is: " + ip, "status": "ok"})

class RelaySerializer(serializers.Serializer):
    message = serializers.CharField(required=True)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip 

def query_params_token_verify(request):
    TOKEN = request.query_params.get("token", "")
    if not TOKEN == bc.BOT_SERVER_GET_REQUEST_TOKEN:
        return Response({"error": "Invalid token"}, status=403)

    # remove the 'token' query parameter
    query_params = request.query_params.copy()
    query_params.pop("token")
    return query_params

def get_internal_api(route):
    return f"http://localhost:{bc.INTERNAL_COMMUNICATION_PORT}/{route}"

def interal_api_data_request(route, data):
    return requests.post(get_internal_api(route), json={
        **data,
        "token": bc.INTERNAL_COMMUNICATION_SECRET
    })
    
@api_view(["GET"])
@permission_classes([])
@authentication_classes([])
def get_debug_relay(request):
    
    query_params = query_params_token_verify(request)

    # e.g. http://localhost:3445/get_debug_relay?message=hello&token=test
    serializer = RelaySerializer(data=query_params)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # curl -d '{"message":"Hello world!"}' -H "Content-Type: application/json" -X POST http://localhost:8080/debugSend
    interal_api_data_request("debugSend", data)
    return Response({"status": "ok"})

@api_view(["GET", "POST"])
@permission_classes([])
@authentication_classes([])
def message_send(request, chat_uuid, recipient_uuid):
    
    if request.method == "POST":
        query_params = query_params_token_verify(request)
        serializer = RelaySerializer(data=query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        interal_api_data_request("messageSend", {
            "chat_id": chat_uuid,
            "recipient_id": recipient_uuid,
            "message": data["message"]
        })
        return Response({"status": "ok"})

    elif request.method == "GET":
        
        query_params = query_params_token_verify(request)
        # e.g. http://localhost:3445/c/12345678-1234-1234-1234-123456789012/12345678-1234-1234-1234-123456789012/?token=test&message=hello
        # e.g. http://localhost:3445/c/264a1df1-2bbd-4285-90de-6c8d9d56105e/7c93df7b-24af-4956-8c25-2376c071c269/?token=test&message=hello
        serializer = RelaySerializer(data=query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        interal_api_data_request("messageSend", {
            "chat_id": chat_uuid,
            "recipient_id": recipient_uuid,
            "message": data["message"]
        })
        return Response({"status": "ok"})
    
class MessageSendTitleSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    message = serializers.CharField(required=True)

@api_view(["GET", "POST"])
@permission_classes([])
@authentication_classes([])
def message_send_title(request):
    # requres only a chat title to send a message to, e.g.: 'lw:pre-matching'
    if request.method == "POST":
        query_params = query_params_token_verify(request)
        serializer = MessageSendTitleSerializer(data=query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        interal_api_data_request("messageSendTitle", {
            "title": data["title"],
            "message": data["message"]
        })
        return Response({"status": "ok"})

    elif request.method == "GET":
        query_params = query_params_token_verify(request)
        serializer = MessageSendTitleSerializer(data=query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        interal_api_data_request("messageSendTitle", {
            "title": data["title"],
            "message": data["message"]
        })
        return Response({"status": "ok"}) 