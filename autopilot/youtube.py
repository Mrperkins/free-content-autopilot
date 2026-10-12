"""YouTube API upload called only after manual approval and exact file hash check."""
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES=['https://www.googleapis.com/auth/youtube.upload']

def upload(path,item):
    privacy=os.getenv('YT_PRIVACY','private').lower()
    if privacy not in ('private','unlisted','public'):
        raise RuntimeError('Invalid YouTube privacy setting')
    if privacy!='private' and os.getenv('YT_API_AUDITED')!='true':
        raise RuntimeError('Non-private uploads blocked until Google API audit explicitly acknowledged')
    credentials=Credentials(token=None,refresh_token=os.environ['YT_REFRESH_TOKEN'],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ['YT_CLIENT_ID'],
            client_secret=os.environ['YT_CLIENT_SECRET'],
            scopes=SCOPES)
    credentials.refresh(Request())
    service=build('youtube','v3',credentials=credentials,cache_discovery=False)
    response=service.videos().insert(
        part='snippet,status',
        body={'snippet':{'title':item['title'][:100],
                         'description':item['description'][:5000],
                         'tags':item.get('tags',[])[:12],
                         'categoryId':'27'},
              'status':{'privacyStatus':privacy,
                        'selfDeclaredMadeForKids':False,
                        'containsSyntheticMedia':False}},
        media_body=MediaFileUpload(str(path),mimetype='video/mp4',
                                  resumable=True,chunksize=5*1024*1024))
    result=None
    while result is None: _,result=response.next_chunk()
    return {'id':result['id'],'url':'https://youtube.com/watch?v='+result['id'],
            'requested_privacy':privacy,'note':'YouTube may further restrict visibility'}
