import smdb_api as API
import json, threading
from time import sleep, time
from os import path, walk, mkdir
from fuzzywuzzy import fuzz

class subject:
    def __init__(self, name, username, lvl_up_callback):
        self.name = name
        self.username = username
        self.started_at = None
        self.xp = 50
        self.xp_increment = 1
        self.lvl = 0
        self.started = False
        self._learning = None
        self.lvl_up_callback = lvl_up_callback

    @classmethod
    def load(cls, name, username, lvl_up_callback):
        try:
            with open(path.join("subjects", f"{name}_{username}.json"), 'r') as f:
                tmp = json.load(f)
            ret = cls(tmp["name"], tmp["username"], lvl_up_callback)
            ret.xp = tmp['xp']
            ret.lvl = tmp['lvl']
            ret.xp_increment = tmp['xp_increment']
            return ret
        except:
            return None

    def start(self):
        self.started_at = int(time())
        self.started = True
        self._learning = threading.Thread(target=self.learning)
        self._learning.name = f"{self.username} learning {self.name}"
        self._learning.start()

    def save(self):
        tmp = {'name':self.name, 'username':self.username, 'xp':self.xp, 'lvl': self.lvl, 'xp_increment':self.xp_increment}
        with open(path.join("subjects", f"{self.name}_{self.username}.json"), 'w') as f:
            json.dump(tmp, f)

    def increase_xp(self, bonus=1):
        self.xp += self.xp_increment*bonus
        if self.xp == 100*(1+self.lvl):
            self.lvl += 1
            self.xp = 0
            self.xp_increment += 0.5
            self.lvl_up_callback(self.lvl, self.name)

    def return_stats(self):
        ret = f"{self.name}: {self.lvl} lvl\n"
        ret += f"{100*(1+self.lvl) - self.xp} xp to the next lvl.{' In progress' if self.started else ''}\n"
        return ret

    def learning(self):
        last_hour = last_minute = last_sec = self.started_at
        while self.started:
            now = int(time())
            if now - last_sec >= 30:
                self.increase_xp()
                last_sec = now
            if now - last_minute >= 1800:
                self.increase_xp(1.01)
                last_minute = now
            if now - last_hour >= 3600:
                self.increase_xp(1.02)
                last_hour = now
            sleep(1)
        delta = ((now - self.started_at % 3600) % 1800 )% 30
        self.xp += (self.xp_increment/30) * delta
    
    def stop(self):
        self.stared = False

class user:
    def __init__(self, id, name, subjects, client):
        self.id = id
        self.name = name
        self.client = client
        self.subjects = {}
        if isinstance(subjects, str):
            for _subject in subjects.split(' '):
                self.subjects[_subject] = subject(_subject, name, self.lvl_up_callback)
        else:
            for _subject in subjects:
                self.subjects[_subject] = subject.load(_subject, name, self.lvl_up_callback)
        self.save()

    @classmethod
    def load(cls, name, client):
        if name.endswith('.json'):
            with open(path.join("data", f"{name}"), 'r') as f:
                try:
                    tmp = json.load(f)
                except:
                    return None
            return cls(tmp["id"], tmp["name"], tmp["subjects"], client)
        return None

    def searc_subject(self, subject):
        mx = {}
        for key in self.subjects.keys():
            tmp = fuzz.ratio(subject.lower(), key.lower())
            if 'value' not in mx or mx["value"] < tmp:
                    mx["key"] = key
                    mx["value"] = tmp
        if mx['value'] > 90:
            return mx['key'], True
        else:
            return mx['key'], False

    def start(self, subject):
        if subject not in self.subjects:
            ret = self.searc_subject(subject)
            if ret[1]:
                subject = ret[0]
            else:
                self.client.send_message(f"You probably wanted {ret[0]}.", destination=self.id)
                return
        self.subjects[subject].start()
        self.client.send_message(f"Started {subject}.", destination=self.id)

    def lvl_up_callback(self, lvl, subject_name):
        self.client.send_message(f"You reached lvl {lvl} in {subject_name}!", destination=self.id)
    
    def add_subject(self, _subject):
        if _subject != "":
            self.subjects[_subject] = subject(_subject, self.name, self.lvl_up_callback)
            self.subjects[_subject].save()
            self.client.send_message(f"Added {_subject} to your subjects!", destination=self.id)
        else:
            self.client.send_message("You need to specify the subject you want to add!", destination=self.id)

    def stop(self, subject):
        if subject not in self.subjects:
            ret = self.searc_subject(subject)
            if ret[1]:
                subject = ret[0]
            else:
                self.client.send_message(f"You probably wanted {ret[0]}.", destination=self.id)
                return
        self.subjects[subject].stop()
        self.client.send_message(f"Stopped {subject}.", destination=self.id)
        self.save()

    def get_status(self, subject):
        to_send = "```\n"
        if subject != "":
            to_send += self.subjects[subject].return_stats()
        else:
            for subject in self.subjects.values():
                to_send += subject.return_stats()
        to_send += "```"
        self.client.send_message(to_send, destination=self.id)

    def remove_subject(self, subject):
        if subject not in self.subjects:
            ret = self.searc_subject(subject)
            if ret[1]:
                subject = ret[0]
            else:
                self.client.send_message(f"You probably wanted {ret[0]}.", destination=self.id)
                return
        del self.subjects[subject]
        self.client.send_message(f"{subject} removed!", destination=self.id)

    def save(self):
        tmp = {}
        tmp["id"] = self.id
        tmp["name"] = self.name
        tmp["subjects"] = list(self.subjects.keys())
        with open(path.join("data", f"{self.name}.json"), "w") as f:
            json.dump(tmp, f)
        for subject in self.subjects.values():
            subject.save()

users = {}
client = None

def create_profile(userID, subjects):
    name = client.get_username(userID)
    users[userID] = user(userID, name, subjects, client)

def start(userID, subject):
    users[userID].start(subject)

def stop(userID, subject):
    users[userID].stop(subject)

def XPStatus(userID, subject):
    users[userID].get_status(subject)

def load():
    for _, _, names, in walk("data"):
        for name in names:
            tmp = user.load(name, client)
            if tmp is not None:
                users[tmp.id] = tmp

def add_subject(userID, subject):
    users[userID].add_subject(subject)

def remove_subject(userID, subject):
    users[userID].remove_subject(subject)

if __name__ == "__main__":
    if not path.exists("data"):
        mkdir("data")
    if not path.exists("subjects"):
        mkdir("subjects")
    client = API.API("XPBot", "19927a7bf1dbf16d70d6dad81ed5a45ef60ab6f41645c68feaa3b870e3e9c65a")
    load()
    client.validate()
    client.create_function("createprofile", "Creates a profile, with the given subjects.\nUsage: &createprofile [subject1 subject2 ... subjectx]\nCategory: USER",
                            create_profile, return_value=[API.USER_INPUT, API.SENDER])
    client.create_function("start", "Starts the learning of the selected subject.\nUsage: &start <subject1>\nCategory: USER",
                            start, return_value=[API.USER_INPUT, API.SENDER])
    client.create_function("stop", "Stops the learning of the selected subject.\nUsage: &stop <subject1>\nCategory: USER",
                            stop, return_value=[API.USER_INPUT, API.SENDER])
    client.create_function("addsubject", "Adds a subject to your list.\nUsage: &addsubject <subject1>\nCategory: USER",
                            add_subject, return_value=[API.USER_INPUT, API.SENDER])
    client.create_function("removesubject", "Removes a subject from your list.\nUsage: &removesubject <subject1>\nCategory: USER",
                            remove_subject, return_value=[API.USER_INPUT, API.SENDER])
    client.create_function("XPStatus", "Returns either the selected subject's status, or the useres current status for every subject.\nUsage: &XPStatus <optional subject1>\nCategory: USER",
                            XPStatus, return_value=[API.USER_INPUT, API.SENDER])