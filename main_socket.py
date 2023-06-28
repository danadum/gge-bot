import json
import math
import logging
from datetime import datetime
from threading import Thread
import time
import websocket
from secondary_socket import SecondarySocket


class MainSocket(websocket.WebSocketApp):
    def __init__(self, url, base, nom, mdp):
        super().__init__(url, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.base = base
        self.nom = nom
        self.mdp = mdp
        self.details_cp = None
        self.dernier_gaa = -1
        self.roue = -1
        self.voyante = -1
        self.coms_en_mouvement = []
        self.attaques_en_cours = []
        self.temp_serveur = None
        self.temp_socket = None

    def on_open(self, ws):
        logging.error(f"### [{datetime.now()}] Main socket connected ###")
        time.sleep(1)
        self.send("""<msg t='sys'><body action='verChk' r='0'><ver v='166' /></body></msg>""")
        self.send("""<msg t='sys'><body action='autoJoin' r='-1'></body></msg>""")
        self.send("""<msg t='sys'><body action='login' r='0'><login z='EmpireEx_3'><nick><![CDATA[]]></nick><pword><![CDATA[1065004%fr%0]]></pword></login></body></msg>""")
        self.send(f"""%xt%EmpireEx_3%lli%1%{{"CONM":175,"RTM":24,"ID":0,"PL":1,"NOM":"{self.nom}","PW":"{self.mdp}","LT":null,"LANG":"fr","DID":"0","AID":"1674256959939529708","KID":"","REF":"https://empire.goodgamestudios.com","GCI":"","SID":9,"PLFID":1}}%""")

    def run(self):
        while self.sock is not None:
            self.send("""%xt%EmpireEx_3%pin%1%<RoundHouseKick>%""")
            self.send("""%xt%EmpireEx_3%sei%1%{}%""")
            self.send("""%xt%EmpireEx_3%gcs%1%{}%""")
            if self.details_cp is not None:
                self.send(f"""%xt%EmpireEx_3%gaa%1%{{"KID":0,"AX1":{self.details_cp[1] // 13 * 13},"AY1":{self.details_cp[2] // 13 * 13},"AX2":{12 + self.details_cp[1] // 13 * 13},"AY2":{12 + self.details_cp[2] // 13 * 13}}}%""")
            time.sleep(60)

    def on_message(self, ws, message):
        message = message.decode('UTF-8')
        if message[:12] == "%xt%lli%1%0%":
            Thread(target=self.run).start()
        elif message[:10] == "%xt%lli%1%" and message[10] != "0":
            self.close()
        elif message[:12] == "%xt%sei%1%0%":
            data = json.loads(message[12:-1])
            for event in data["E"]:
                if event["RS"] > 30 and event["EID"] in [7, 75, 90]:
                    temps = int(event['RS']) + int(time.time())
                    contenu = str(event.get("WID") or event.get("BID") or event.get("TID"))
                    reduction = event.get('DIS') or 0
                    old_event = self.base.get(f"/events/{event['EID']}", None)
                    if old_event["temps"] < int(time.time()) or old_event["contenu"] != contenu or old_event["reduction"] != reduction:
                        self.base.patch(f"/events/{event['EID']}", {"temps": temps, "contenu": contenu, "reduction": reduction, "nouveau": 1})
                elif event["EID"] == 106 and self.temp_serveur != ["RE", event["TSID"]]:
                    if event["IPS"] == 0:
                        if event["TSID"] == 16:
                            self.send("""%xt%EmpireEx_3%sbp%1%{"PID":2358,"BT":0,"TID":106,"AMT":1,"KID":0,"AID":-1,"PC2":-1,"BA":0,"PWR":0,"_PO":-1}%""")
                            self.send("""%xt%EmpireEx_3%tsc%1%{"ID":40,"OC2":0,"PWR":0,"GST":2}%""")
                        else:
                            self.send("""%xt%EmpireEx_3%tsc%1%{"ID":31,"OC2":1,"PWR":0,"GST":2}%""")
                        time.sleep(1)
                    self.send("""%xt%EmpireEx_3%glt%1%{"GST":2}%""")
                    self.temp_serveur = ["RE", event["TSID"]]
                elif event["EID"] == 113 and self.temp_serveur != ["LACIS", event["TSID"]]:
                    if event["IPS"] == 0:
                        self.send("""%xt%EmpireEx_3%tsc%1%{"ID":34,"OC2":1,"PWR":0,"GST":3}%""")
                        time.sleep(1)
                    self.send("""%xt%EmpireEx_3%glt%1%{"GST":3}%""")
                    self.temp_serveur = ["LACIS", event["TSID"]]
                elif event["EID"] == 117 and event.get("FTDC") == 1:
                    now = int(time.time())
                    if now > self.voyante + 30:
                        self.voyante = now
                        self.send("""%xt%EmpireEx_3%ftl%1%{}%""")
                elif event["EID"] == 15 and event.get("OP") is not None and event.get("OP")[0] < 3:
                    now = int(time.time())
                    if now > self.roue + 30:
                        self.roue = now
                        self.send("""%xt%EmpireEx_3%lws%1%{"LWET":0}%""")
        elif message[:12] == "%xt%gcs%1%0%":
            data = json.loads(message[12:-1])
            if data["CHR"][0]["FOA"] > 0:
                self.send("""%xt%EmpireEx_3%sct%1%{"CID":1,"OID":6001,"IF":1}%""")
            elif data["CHR"][1]["FOA"] > 0:
                self.send("""%xt%EmpireEx_3%sct%1%{"CID":2,"OID":6002,"IF":1}%""")
            elif data["CHR"][2]["FOA"] > 0:
                self.send("""%xt%EmpireEx_3%sct%1%{"CID":3,"OID":6003,"IF":1}%""")
        elif message[:12] == "%xt%soe%1%0%":
            data = message.split("%")
            if int(data[7]) > 30:
                temps = int(data[7]) + int(time.time())
                old_event = self.base.get("/events/999", None)
                if old_event["temps"] < int(time.time()) or old_event["contenu"] != data[5]:
                    self.base.patch("/events/999", {"temps": temps, "contenu": data[5], "reduction": 0, "nouveau": 1})
        elif message[:12] == "%xt%glt%1%0%":
            data = json.loads(message[12:-1])
            self.temp_socket = SecondarySocket(f"wss://{data['TSIP']}", self.base, data["TSZ"], data["TLT"], self.temp_serveur[0], self)
            Thread(target=self.temp_socket.run_forever, kwargs={'reconnect': False}).start()
        elif message[:12] == "%xt%gbd%1%0%":
            data = json.loads(message[12:-1])
            vert = next(filter(lambda monde: monde["KID"] == 0, data["gcl"]["C"]))
            self.details_cp = next(filter(lambda chateau: chateau["AI"][0] == 1, vert["AI"]))["AI"]
        elif message[:12] == "%xt%gaa%1%0%":
            data = json.loads(message[12:-1])
            now = int(time.time())
            if now > self.dernier_gaa + 300:
                self.dernier_gaa = now
                Thread(target=self.launch_attacks, args=(data, )).start()
        elif message[:12] == "%xt%gam%1%0%" and self.details_cp is not None:
            data = json.loads(message[12:-1])
            moves = [move for move in data["M"] if move["M"]["OID"] == self.details_cp[4] and move.get("UM") is not None]
            self.coms_en_mouvement = [move["UM"]["L"].get("ID") for move in moves]
            self.attaques_en_cours = [move["M"]["TA"] for move in moves if len(move["M"]["TA"]) == 7 and move["M"]["TA"][0] == 2]
        elif message[:12] == "%xt%adi%1%0%":
            data = json.loads(message[12:-1])
            commandant = next(filter(lambda com: com["ID"] not in self.coms_en_mouvement, data["gli"]["C"]), None)
            type_soldats = 0
            if next(filter(lambda obj: obj[0] == 9, data["gui"]["I"]), [0, 0])[1] > 320:
                type_soldats = 9
            elif next(filter(lambda obj: obj[0] == 10, data["gui"]["I"]), [0, 0])[1] > 320:
                type_soldats = 10
            if commandant is not None and type_soldats != 0:
                level = math.floor(1.9 * data["gaa"]["AI"][4] ** 0.555) + 1
                max_soldats = min(260, 5 * level + 8) if level <= 69 else 320
                limite_flanc = math.ceil(0.2 * max_soldats)
                limite_front = max_soldats - 2 * limite_flanc
                vague = f"""{{"L":{{"T":[],"U":[[{type_soldats},{limite_flanc}]]}},"R":{{"T":[],"U":[[{type_soldats},{limite_flanc}]]}},"M":{{"T":[],"U":[]}}}}"""
                vagues = f"""[{",".join(1 * [vague])}]"""
                cour = f"""[[{type_soldats},{100 + level}]]"""
                attaque = f"""%xt%EmpireEx_3%cra%1%{{"SX":{self.details_cp[1]},"SY":{self.details_cp[2]},"TX":{data["gaa"]["AI"][1]},"TY":{data["gaa"]["AI"][2]},"KID":0,"LID":{commandant["ID"]},"WT":0,"HBW":1007,"BPC":0,"ATT":0,"AV":0,"LP":0,"FC":0,"PTT":0,"SD":0,"ICA":0,"CD":99,"A":{vagues},"BKS":[],"AST":[],"RW":{cour}}}%"""
                logging.error(attaque)
                self.send(attaque)

    def launch_attacks(self, data):
        for map_object in data["AI"]:
            if len(map_object) == 7 and map_object[0] == 2 and map_object[5] < 0:
                self.send("""%xt%EmpireEx_3%gam%1%{}%""")
                time.sleep(1)
                if next(filter(lambda fc: fc[1] == map_object[1] and fc[2] == map_object[2], self.attaques_en_cours), None) is None:
                    self.send(f"""%xt%EmpireEx_3%adi%1%{{"SX":{self.details_cp[1]},"SY":{self.details_cp[2]},"TX":{map_object[1]},"TY":{map_object[2]},"KID":0}}%""")
                    time.sleep(5)

    def on_error(self, ws, error):
        logging.error("### error in main socket ###")
        logging.error(error)
        self.close()

    def on_close(self, ws, close_status_code, close_msg):
        logging.error(f"### [{datetime.now()}] Main socket closed ###")

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
