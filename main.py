import os, sys
import pandas as pd
import requests
import json
import time
from datetime import datetime



class Config():
    def __init__(self):
        if getattr(sys, 'frozen', False):
            #test.exe로 실행한 경우,test.exe를 보관한 디렉토리의 full path를 취득
            self.ROOT_DIR = os.path.dirname(os.path.abspath(sys.executable))
        else:
            #python test.py로 실행한 경우,test.py를 보관한 디렉토리의 full path를 취득
            self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        self.RESULT_DIR = os.path.join(self.ROOT_DIR, 'result')
        self.DATA_DIR = os.path.join(self.ROOT_DIR, 'data')
        self.game_ids = None
        self.files = []
        self.ID = ''

    def get_config(self):
        self.file = [i for i in os.listdir(self.DATA_DIR) if 'xlsx' in i]
        while True:
            try:
                id = pd.read_excel(os.path.join(self.DATA_DIR, self.file[0]))
                break
            except:
                print('엑셀이 열려있습니다. config id')
        self.ID = id.loc[0,'ID']
        if os.listdir(self.RESULT_DIR):
            while True:
                try:
                    self.game_ids = pd.read_excel(os.path.join(self.RESULT_DIR, os.listdir(self.RESULT_DIR)[0]))
                    self.game_ids = self.game_ids.loc[:, '게임id']
                    self.game_ids = list(self.game_ids)
                    if len(self.game_ids)==0:
                        self.game_ids = None
                    break
                except:
                    print('엑셀이 열려있습니다. config result')
        else:
            self.game_ids = None


class PuuidParser():
    def __init__(self):
        self.user_id = config.ID
        self.url = 'https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/{ID}'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Charset': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://developer.riotgames.com',
            'X-Riot-Token': 'RGAPI-4622da6d-85d9-4943-9409-e4db774c4ebd'
            }

    def get_puuid(self):
        response = requests.request("GET", self.url.format(ID=self.user_id), headers=self.headers)
        data = response.json()
        return data['id'], data['puuid']

class NowPlayingParser(PuuidParser):
    def __init__(self):
        super().__init__()
        self.live_client_url = 'https://127.0.0.1:2999/liveclientdata/allgamedata'

    def is_now_playing(self):
        summoneId, puuid = self.get_puuid()
        response = requests.request("GET", 'https://kr.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/{summoneId}'.format(summoneId=summoneId), headers=self.headers)
        if response.status_code == 200:
            return response
        else:
            return False
    
    def get_playing_info(self, response):
        data = response.json()
        summoner_name = [i['summonerName'] for i in data['participants']]
        summoner_id = [i['summonerId'] for i in data['participants']]
        champion_id = [i['championId'] for i in data['participants']]
        game_id = data['gameId']
        game_start_time = data['gameStartTime']
        return summoner_name, summoner_id, game_id,game_start_time, champion_id

class LiveDataParser():
    def __init__(self):
        self.now_playing = ''
        self.is_now_playing = ''
        self.game_ids = config.game_ids
        self.flag = 1

    def get_parser(self):
        self.now_playing = NowPlayingParser()
        self.is_now_playing = self.now_playing.is_now_playing()
        while True:
            print('요청 중')
            if self.is_now_playing:
                self.summoner_name, self.summoner_id, self.game_id, self.get_start_time, self.champion_id = self.now_playing.get_playing_info(self.is_now_playing)
                if self.game_ids and self.game_id in self.game_ids:
                    print('게임 이미 수집되었습니다')
                    self.flag = 0
                    break
                else:
                    self.data_1 = {}
                    self.data_2 = {}
                    time.sleep(5)
                    break
            else:
                time.sleep(5)
                self.flag = 0
                print('게임을 시작하지 않았습니다.')
                self.is_now_playing = self.now_playing.is_now_playing()

    def get_live_data(self):
        data = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', verify=False)
        data = data.json()

        self.data_1['ID'] = self.summoner_id
        self.data_1['이름'] = self.summoner_name
        self.data_1['날짜'] = [datetime.now()]*len(self.data_1['이름'])
        self.data_1['게임 시작 시간'] = [self.get_start_time]*len(self.data_1['이름'])
        self.data_1['게임id'] = [self.game_id]*len(self.data_1['이름'])
        data_1 = pd.DataFrame(self.data_1)
        
        all_players = data['allPlayers']
        self.data_2['챔피언'] = [player['championName'] for player in all_players]
        self.data_2['이름'] = [player['summonerName'] for player in all_players]
        self.data_2['팀'] = [player['team'] for player in all_players]
        self.data_2['스펠 1'] = [player['summonerSpells']['summonerSpellOne']['displayName'] for player in all_players]
        self.data_2['스펠 2'] = [player['summonerSpells']['summonerSpellTwo']['displayName'] for player in all_players]
        self.data_2['룬1'] = [player['runes']['keystone']['displayName'] for player in all_players]
        self.data_2['룬2'] = [player['runes']['primaryRuneTree']['displayName'] for player in all_players]
        self.data_2['룬3'] = [player['runes']['secondaryRuneTree']['displayName'] for player in all_players]
        
        events = data['events']
        self.data_2['퍼스트블러드'] = [event['Recipient'] for event in events['Events'] if event['EventName'] == 'FirstBlood']*len(self.data_2['이름'])
        while True:
            if self.data_2['퍼스트블러드']:
                data_2 = pd.DataFrame(self.data_2)
                merged_data = pd.merge(data_1, data_2, on='이름', how='left')
                break
            else:
                
                time.sleep(60)
                try:
                    data = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', verify=False)
                    data = data.json()
                    events = data['events']
                    self.data_2['퍼스트블러드'] = [event['Recipient'] for event in events['Events'] if event['EventName'] == 'FirstBlood']*len(self.data_2['이름'])
                    print('퍼스트 블러드가 아직 나오지 않았습니다.')
                except:
                    print('게임이 종료 되었습니다.')

        return merged_data


config = Config()
config.get_config()

while True:
        data_parser = LiveDataParser()
        data_parser.get_parser()
        if data_parser.flag==1:
            while True:
                try:
                    if config.game_ids:
                        origin_data = pd.read_excel(os.path.join(config.RESULT_DIR, os.listdir(config.RESULT_DIR)[0]))
                        origin_data = origin_data.iloc[:,1:]
                        data = data_parser.get_live_data()
                        data = pd.concat([origin_data, data], axis=0)
                        config.game_ids = data.loc[:, '게임id']
                        config.game_ids = list(config.game_ids)
                        data.to_excel(os.path.join(config.RESULT_DIR, 'result.xlsx'))
                        print('데이터가 저장 되었습니다.')
                        time.sleep(10)
                        break
                    else:
                        data = data_parser.get_live_data()
                        data.to_excel(os.path.join(config.RESULT_DIR, 'result.xlsx'))
                        config.game_ids = data.loc[:, '게임id']
                        config.game_ids = list(config.game_ids)
                        print('데이터가 저장 되었습니다.')
                        time.sleep(10)
                        break
                except:
                    print('엑셀이 열려있습니다. return')
        else:
            time.sleep(10)