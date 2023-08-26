from django.http import JsonResponse

from chat.models import UserTeamChatStatus, ChatMessage
from team.models import Team, Member
from user.models import User


# Create your views here.
#def upload_document():

def initial_chat(request,user_id):
    Team_ids= Member.objects.filter(user_id= user_id).values('team_id')
    rooms=[]
    print(Team_ids)
    for team_dict in Team_ids:
        team_id = team_dict['team_id']
        members = Member.objects.filter(team_id=team_id)
        last_message=ChatMessage.objects.filter(team_id=team_id).order_by('-timestamp').first()
        lastMessage={
            'content':last_message.message,
            'username':User.objects.get(id=last_message.user_id).username,
            'timestamp':last_message.timestamp,
        }
        users=[]
        for member in members:
            users.append({
                'username':User.objects.get(id=member.user_id).username,
                'avatar':User.objects.get(id=member.user_id).avatar_url,
            })
        room_data={
            'roomId':team_id,
            'roomName':Team.objects.get(id=team_id).name,
            'unreadCount':UserTeamChatStatus.objects.get(user_id=user_id,team_id=team_id).unread_count,
            'avatar':Team.objects.get(id=team_id).cover_url,
            'index':UserTeamChatStatus.objects.get(user_id=user_id,team_id=team_id).index,
            'lastMessage':lastMessage,
            'users':users,
        }
        rooms.append(room_data)
    return JsonResponse({'rooms':rooms})


