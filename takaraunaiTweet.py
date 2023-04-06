import requests
import os
import json
import openai
from requests_oauthlib import OAuth1Session
import time
import traceback
import tweepy
# from dotenv import load_dotenv

# load_dotenv('.env') 


# Twitter APIの認証情報を設定
bearer_token= os.environ.get("bearer_token")
consumer_key = os.environ.get("consumer_key")
consumer_secret = os.environ.get("consumer_secret")
access_token = os.environ.get("access_token")
access_token_secret = os.environ.get("access_token_secret")

# OpenAI APIの認証情報を設定
openai.api_key = os.environ.get("openai.api_key")

Client = tweepy.Client(bearer_token, consumer_key, consumer_secret, access_token, access_token_secret)

def bearer_oauth(r):
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2FilteredStreamPython"
    return r

def get_rules():
    response = requests.get(
        "https://api.twitter.com/2/tweets/search/stream/rules", auth=bearer_oauth
    )
    if response.status_code != 200:
        raise Exception(
            "Cannot get rules (HTTP {}): {}".format(response.status_code, response.text)
        )
    print(json.dumps(response.json()))
    return response.json()

def delete_all_rules(rules):
    if rules is None or "data" not in rules:
        return None

    ids = list(map(lambda rule: rule["id"], rules["data"]))
    payload = {"delete": {"ids": ids}}
    response = requests.post(
        "https://api.twitter.com/2/tweets/search/stream/rules",
        auth=bearer_oauth,
        json=payload
    )
    if response.status_code != 200:
        raise Exception(
            "Cannot delete rules (HTTP {}): {}".format(
                response.status_code, response.text
            )
        )
    print(json.dumps(response.json()))
 
def set_rules(delete):
    rules = [
        {
            "value":"to:takareinhard"
        }
    ]
    payload = {"add": rules}
    response = requests.post(
        "https://api.twitter.com/2/tweets/search/stream/rules",
        auth=bearer_oauth,
        json=payload,
    )
    if response.status_code != 201:
        raise Exception(
            "Cannot add rules (HTTP {}): {}".format(response.status_code, response.text)
        )
    print(json.dumps(response.json()))
    
    
def get_stream(headers):
    run = 1
    #自動返信が終わったリプのツイートIDを入れる
    replied_tweet_ids = set()
    
    while run:
        try:
            with requests.get(
                "https://api.twitter.com/2/tweets/search/stream", auth=bearer_oauth, stream=True, timeout=30
            ) as response:
                print(response.status_code)
                if response.status_code != 200:
                    raise Exception(
                        "Cannot get stream (HTTP {}): {}".format(
                            response.status_code, response.text
                        )
                    )
                    
                start_time = time.time()
                timeout = 30  # タイムアウト時間（秒）    

                for response_line in response.iter_lines():
                    if time.time() - start_time > timeout:
                        break  # タイムアウト時間が経過した場合、ストリームを閉じる
                    if response_line:
                        json_response = json.loads(response_line)
                        tweet_id = json_response["data"]["id"] #ツイートID
                        reply_text=json_response["data"]["text"] #相手の送ってきた内容

                        # 既に返信したツイートIDであればスキップ
                        if tweet_id in replied_tweet_ids:
                            continue
                        

                        if "占って" in reply_text:
                            
                            completion = openai.ChatCompletion.create(
                                model = 'gpt-3.5-turbo',
                                messages = [
                                    {'role': 'user', 'content': 'あなたは占い師です。水晶玉の中に見えるもので占ってください。日本語で100文字以内でおねがいします。'}
                                ],
                            temperature = 0  
                        )
                            print(completion['choices'][0]['message']['content'])
                            text = completion['choices'][0]['message']['content']
                            
                            Client.create_tweet(
                                text=text,
                                in_reply_to_tweet_id =tweet_id)
                            
                            # 返信済みのツイートIDを記録
                            replied_tweet_ids.add(tweet_id)

                        
                        else:
                            print("リプライありがとうございます！")
                            text ="リプライありがとうございます！"
                            
                            Client.create_tweet(
                                text=text,
                                in_reply_to_tweet_id=tweet_id)

                            # 返信済みのツイートIDを記録
                            replied_tweet_ids.add(tweet_id)
    
        except ChunkedEncodingError as chunkError:
            print(traceback.format_exc())
            time.sleep(6)
            continue
        
        except ConnectionError as e:
            print(traceback.format_exc())
            run+=1
            if run <10:
                time.sleep(6)
                print("再接続します",run+"回目")
                continue
            else:
                run=0
                
        except Exception as e:
            # some other error occurred.. stop the loop
            print("Stopping loop because of un-handled error")
            print(traceback.format_exc())
            run = 0
            
        finally:
            # ストリームが閉じられているかどうかを確認し、必要に応じて閉じる
            if not response.close:
                response.close()
	    
class ChunkedEncodingError(Exception):
    pass

def main():
    rules = get_rules()
    delete = delete_all_rules(rules)
    set = set_rules(delete)
    get_stream(set)
 
if __name__ == "__main__":
    main()
