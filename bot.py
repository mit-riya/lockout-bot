import discord
import time
import math
import random
from discord.ext import commands
from pymongo import MongoClient
import requests
import json
import random
from threading import Timer
import time
uri = "MONGO_URI"
token= "TOKEN"
cluster = MongoClient(uri)
db = cluster['discord-bot']
servers = db['servers']
participantsList = db['participantsList']
tourney_status = db['tourney_status']
storage = db['storage']
current_round = db['current_round']
current_matches=db['current_matches']
intents = discord.Intents().all()
client = commands.Bot(command_prefix=".", intents=intents)
botName = "Tatakae"

@client.command()
async def match_updates(ctx,player_1,player_2):
    id1 = int(player_1[2:len(player_1)-1])
    id2 = int(player_2[2:len(player_2)-1])
    flag=False
    match_={}
    for match in current_matches.find_one({"server":ctx.guild.id})["matches"]:
        if(match["id_s"]==[id1,id2] or match["id_s"]==[id2,id1]):
            flag=True
            match_=match
            break
    if(flag==False):
        embed=discord.Embed(
        title="No live match among mentioned players!",
        color=discord.Color.dark_gold()
        )
        await ctx.send(embed=embed)

    current_time=time.ctime()[11:19]
    hours=int(current_time[0:2])
    minutes=int(current_time[3:5])
    time_elapsed=(hours-match_["Start_Time"][0])*60+(minutes-match_["Start_Time"][1])
    score1,score2=match_["Scores"][0],match_["Scores"][1]
    id1,id2=match_["id_s"][0],match["id_s"][1]
    embed=discord.Embed(
        title="Match_Updates",
        description=f"<@{id1}> : {score1}   <@{id2}> : {score2}",
        color=discord.Color.magenta()
        )
    index=1
    for x in match_["Problems"]:
        if(x['status'] == 0):
            embed.add_field(name=f"{index}. {x['name']} ({index*100})", value=f"https://codeforces.com/contest/{x['contestId']}/problem/{x['index']}",inline=False)
        else:
            embed.add_field(
                name=f"{index}. {x['name']} ({index*100})", value=f"This problem has been solved",inline=False)
        index=index+1
    embed.set_footer(text=f"Remaining Time : {60-time_elapsed} minutes")
    await ctx.send(embed=embed)

def update():
    new_match_list=[]
    all_current_matches=current_matches.find()
    for currentmatches in all_current_matches:
        if(len(currentmatches["matches"])!=0):
            for match in currentmatches["matches"]:
                updated_match=match
                handles=match["handles"]
                match_problems=match["Problems"]
                scores=match["Scores"]
                start_time=match["Start_Time"]
                handle1=handles[0]
                handle2=handles[1]
                url1=f"https://codeforces.com/api/user.status?handle={handle1}&from=1&count=10"
                url2=f"https://codeforces.com/api/user.status?handle={handle2}&from=1&count=10"
                response_API=requests.get(url1)
                data=response_API.text
                parse_json=json.loads(data)
                submissions=parse_json['result']
                score1=scores[0]
                score2=scores[1]
                index=1
                for x in match_problems:
                    for y in submissions:
                        if(y['problem']['name']==x['name']and y['verdict']=="OK"and x['status']==0):
                            x['status']=1
                            score1=score1+100*index
                            continue
                    index=index+1
                response_API=requests.get(url2)
                data=response_API.text
                parse_json=json.loads(data)
                submissions=parse_json['result']
                index=1
                for x in match_problems:
                    for y in submissions:
                        if(y['problem']['name']==x['name']and y['verdict']=="OK"and x['status']==0):
                            x['status']=1
                            score2=score2+100*index
                            continue
                    index=index+1
                updated_match["Problems"]=match_problems
                updated_match["Scores"]=[score1,score2]
                new_match_list.append(updated_match)
                current_time=time.ctime()[11:19]
                hours=int(current_time[0:2])
                minutes=int(current_time[3:5])
                seconds=int(current_time[6:8])
                time_elapsed=(hours-start_time[0])*60+(minutes-start_time[1])
                print(time_elapsed)
            current_matches.update_one({"server":currentmatches["server"]},{"$set":{"matches":new_match_list}})   
    Timer(10,update).start()
        
update()


@client.event
async def on_guild_join(guild):
    res = servers.find_one({"_id": guild.id})
    if res is None:
        # print(guild)
        text_channel = guild.text_channels[0]
        servers.insert_one({"_id": guild.id,
                            "text_channel": text_channel.id,
                            "tourney_name": "--",
                            "tourney_status": False,
                            "current_round": None})
        current_matches.insert_one({"server": guild.id,
                                    "matches": []})
        participantsList.insert_one({"server": guild.id,
                                    "contestants": []})
        storage.insert_one({"server": guild.id,
                            "storage": []})            
        embed = discord.Embed(title="Lockout Bot Added Successfully!",
                              description="You are now ready to organise tournaments", color=0xffa800)
        embed.set_thumbnail(
            url="https://cdn-icons-png.flaticon.com/512/1355/1355961.png")
        embed.add_field(name="Bot Name", value="Lockout Bot", inline=True)
        embed.add_field(name="Nick Name", value="Tatakae", inline=True)
        await text_channel.send(embed=embed)



@client.command()
# @commands. has_role('Tourney Manager')
async def startRegister(ctx, tourneyName: str):
    print(tourneyName)
    thisServer = servers.find_one({"_id": ctx.guild.id})
    text_channel_n = thisServer["text_channel"]
    global text_channel
    for x in ctx.guild.text_channels:
        if x.id == text_channel_n:
            text_channel = x

    if thisServer["tourney_name"] == "--":
        servers.update_one({"_id": ctx.guild.id}, {
                           "$set": {"tourney_name": tourneyName}})
        embed = discord.Embed(
            title="Tournament Started",
            description=f"Please ask participants to register themselves with **p!registerMe seed** where seed is the "
                        f"parameter on which you want to order people",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Please first close the running tournament",
            description=f"A tournament **{thisServer['tourney_name']}** is already running on this server, please stop it first to start a new one."
                        f"\nStop using p!stopTourney",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)


@client.command()
# @commands. has_role('Tourney Manager')
async def stopTourney(ctx):
    thisServer = servers.find_one({"_id": ctx.guild.id})
    text_channel_n = thisServer["text_channel"]
    global text_channel
    for x in ctx.guild.text_channels:
        if x.id == text_channel_n:
            text_channel = x

    if thisServer["tourney_name"] == "--":
        embed = discord.Embed(
            title="No Tourney running",
            description="No tourney is currently running on this server.",
            color=discord.Color.gold()
        )
        await text_channel.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Tourney stopped:(",
            description=f"The tourney **{thisServer['tourney_name']}** has been stopped.",
            color=discord.Color.red()
        )
        embed.set_author(name=botName)
        servers.update_one({"_id": ctx.guild.id}, {"$set": {"tourney_name": "--","tourney_status": False, "current_round": None}})
        storage.update_one({"server":ctx.guild.id},{"$set":{"storage": []}})
        participantsList.update_one({"server":ctx.guild.id},{"$set":{"contestants": []}})
        await ctx.send(embed=embed)



@client.command()
# @commands. has_role('Tourney Manager')
async def currentRound(ctx):
    thisServer = servers.find_one({"_id": ctx.guild.id})
    text_channel_n = thisServer["text_channel"]
    global text_channel
    for x in ctx.guild.text_channels:
        if x.id == text_channel_n:
            text_channel = x

    current_round = thisServer["current_round"]
    if(current_round == None):
        embed = discord.Embed(
            title="No tourney is currently active on this server. ",
            color=discord.Color.gold()
        )
    else:
        embed = discord.Embed(
            title=f"Current round : {current_round} ",
            color=discord.Color.gold()
        )
    
    embed.set_author(name=botName)
    await text_channel.send(embed=embed)


@client.command()
# @commands. has_role('Tourney Manager')
async def startTourney(ctx):
    thisServer = servers.find_one({"_id": ctx.guild.id})
    text_channel_n = thisServer["text_channel"]
    global text_channel
    for x in ctx.guild.text_channels:
        if x.id == text_channel_n:
            text_channel = x

    checkForStartTourney = thisServer["tourney_status"]

    if checkForStartTourney == True:
        embed = discord.Embed( 
            title="Tournament Already Started",
            description="Tounament has already started so nothing can be changed.",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)
        return

    if thisServer["tourney_name"] == "--":
        embed = discord.Embed(
            title="No Tourney registered",
            description="No tourney is currently started for registration on this server. ",
            color=discord.Color.gold()
        )
        await text_channel.send(embed=embed)

    elif len(participantsList.find_one({"server": ctx.guild.id})["contestants"]) == 0:
        embed = discord.Embed(
            title="No registrations",
            description="No participants registered, cannot start the Tourney. Participants can register using p!registerMe",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)

    elif len(participantsList.find_one({"server": ctx.guild.id})["contestants"]) == 1:
        embed = discord.Embed(
            title="Single registrant",
            description="Cannot start a tourney with a single participant.",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)

    else:
        servers.update_one({"_id": ctx.guild.id}, {
                           "$set": {"tourney_status": True}})

        match_builder(ctx)

        embed = discord.Embed(
            title=f"Tourney started :D",
            description=f"The tourney {thisServer['tourney_name']} has been started.",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)
        update()
  

@client.command()
async def startMatch(ctx, player_1, player_2, rting: int):
    thisServer = servers.find_one({"_id": ctx.guild.id})
    text_channel_n = thisServer["text_channel"]
    global text_channel
    for x in ctx.guild.text_channels:
        if x.id == text_channel_n:
            text_channel = x
    match_list=current_matches.find_one({"server":ctx.guild.id})['matches']
    dic={}
    dic.update({"text_channel":"-"})
    str1 = player_1[2:len(player_1)-1]
    str2 = player_2[2:len(player_2)-1]
    print(str1, str2)
    handle1 = None
    handle2 = None
    participants = participantsList.find_one({"server": ctx.guild.id})["contestants"]
    for i in participants:
        if(str1 == str(i["id"])):
            handle1 = i["cf_handle"]
        if(str2 == str(i["id"])):
            handle2 = i["cf_handle"]
    if(handle1==handle2):
        embed = discord.Embed(
            title="Error!",
            description="Both Players can't be same",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    print(handle1,handle2)
    flag=False
    curr_round = servers.find_one({"_id": ctx.guild.id})["current_round"]
    current_round_matches=storage.find_one({"server": ctx.guild.id})["storage"][curr_round - 1]["matches"]
    for match in current_round_matches:
        print(match)
        if((handle1==match["player1"] and handle2==match["player2"]) or (handle1==match["player2"] and handle2==match["player1"])):
            flag=True
            break
    if(flag==False):
        embed = discord.Embed(
            title="Error!",
            description="Mentioned Players don't have a match in current round, check again",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    flag=False
    for match in current_matches.find_one({"server":ctx.guild.id})["matches"]:
        if(match["handles"]==[handle1,handle2] or match["handles"]==[handle2,handle1]):
            flag=True
            break
    if(flag):
        embed=discord.Embed(
        title="Match has already started between mentioned players",
        color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    dic.update({"handles":[handle1,handle2]})
    dic.update({"id_s":[int(str1),int(str2)]})
    rating = rting
    url = f"https://codeforces.com/api/problemset.problems?implementation"

    response_API = requests.get(url)
    data = response_API.text
    parse_json = json.loads(data)
    problems = parse_json['result']['problems']

    random.shuffle(problems)
    problem_list = []
    c = 0
    for i in problems:  
        if(i.get('rating') == rating and unsolved_checker(i["contestId"], i["index"], handle1) and unsolved_checker(i["contestId"], i["index"], handle2) ):
            i['status']=0
            problem_list.append(i)
            rating += 100
            c += 1
        if(c == 5):
            break
    embed = discord.Embed(
        title="Problems For This Round",
        color=discord.Color.dark_gold()
    )
    index=1
    for i in problem_list:
        embed.add_field(
            name=f"{index}. {i['name']} ({index*100})", value=f"https://codeforces.com/contest/{i['contestId']}/problem/{i['index']}", inline=False)
        index=index+1
    
    embed.set_footer(text="You have 60 minutes to solve the questions :)")
    dic.update({"Problems":problem_list})
    dic.update({"Scores":[0,0]})
    start_time=time.ctime()[11:19]
    hours=int(start_time[0:2])
    minutes=int(start_time[3:5])
    seconds=int(start_time[6:8])
    dic.update({"Start_Time":[hours,minutes,seconds]})
    match_list.append(dic)
    current_matches.update_one({"server":ctx.guild.id},{"$set":{"matches":match_list}})
    await ctx.send(embed=embed)
    
    

@client.command()
async def registerMe(ctx, cf_handle):
    thisServer = servers.find_one({"_id": ctx.guild.id})
    text_channel_n = thisServer["text_channel"]
    global text_channel
    for x in ctx.guild.text_channels:
        if x.id == text_channel_n:
            text_channel = x

    checkForStartTourney = thisServer["tourney_status"]

    if checkForStartTourney == True:
        embed = discord.Embed(
            title="Tournament Already Started",
            description="Tounament has already started so nothing can be changed.",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)
        return

    if thisServer["tourney_name"] == "--":
        embed = discord.Embed(
            title="No Tourney",
            description=f"{ctx.author.mention} there is no ongoing tournament",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)
        return

    participantsListTemp = participantsList.find_one({"server": ctx.guild.id})


    for x in participantsListTemp["contestants"]:
        if x['id'] == ctx.author.id:
            embed = discord.Embed(
                title="Already Registered",
                description=f"{ctx.author.mention} you are already registered, please wait till tournament"
                            f" is started. If trying to change your"
                            f"seed then first unregister yourself then again register.",
                color=discord.Color.gold()
            )
            embed.set_author(name=botName)
            await text_channel.send(embed=embed)
            return

    participantsList.update_one({"server": ctx.guild.id},
                                {"$push": {"contestants": {"id": ctx.author.id, "cf_handle": cf_handle}}})

    embed = discord.Embed(
        title="You are Registered",
        description=f"{ctx.author.mention} you are now registered for the tournament.",
        color=discord.Color.gold()
    )
    embed.set_author(name=botName)
    await text_channel.send(embed=embed)

@client.command()
async def stopMatch(ctx, player_1, player_2):
    thisServer = servers.find_one({"_id": ctx.guild.id})
    text_channel_n = thisServer["text_channel"]
    global text_channel
    for x in ctx.guild.text_channels:
        if x.id == text_channel_n:
            text_channel = x

    match_list=current_matches.find_one({"server": ctx.guild.id})['matches']

    str1 = player_1[2:len(player_1)-1]
    str2 = player_2[2:len(player_2)-1]
    handle1 = None
    handle2 = None
    participants = participantsList.find_one({"server": ctx.guild.id})["contestants"]
    for i in participants:
        if(str1 == str(i["id"])):
            handle1 = i["cf_handle"]
        if(str2 == str(i["id"])):
            handle2 = i["cf_handle"]
    
    winner = None
    win_handle = None
    temp = []
    for i in match_list:
        if(i["handles"][0] == handle1 and i["handles"][1] == handle2):
            if(i["Scores"][0] > i["Scores"][1]):
                winner = str1
                win_handle = handle1
            else:
                winner = str2
                win_handle = handle2
            break
        elif(i["handles"][1] == handle1 and i["handles"][0] == handle2):
            if(i["Scores"][0] > i["Scores"][1]):
                winner = str2
                win_handle = handle2
            else:
                winner = str1
                win_handle = handle1
            break
        else:
            temp.append(i)

        
    current_matches.update_one({"server": ctx.guild.id}, {"$set":{"matches": temp}})

    curr_round = servers.find_one({"_id": ctx.guild.id})["current_round"]

    rounds = storage.find_one({"server": ctx.guild.id})["storage"]

    embed = None

    if(curr_round == len(rounds)):
        embed = discord.Embed(
            title="Congratulations " + win_handle + "!",
            color=discord.Color.dark_blue(),
            description="you have won the tournament :D"
        )

        participantsList.update_one({"server": ctx.guild.id},{"$set":{"contestants": []}})
        servers.update_one({"_id": ctx.guild.id},{"$set":{"tourney_name": "--","tourney_status": False,"current_round": None}})
        storage.update_one({"server": ctx.guild.id},{"$set":{"storage": []}})
        current_matches.update_one({"server": ctx.guild.id},{"$set":{"matches": []}})

    
    else:
        embed = discord.Embed(
            title="Congratulations " + win_handle + "!",
            color=discord.Color.dark_gold(),
            description="you have won this round"
        )

        matches = rounds[curr_round-1]["matches"]
        for i in range(len(matches)):
            if((matches[i]["player1"] == handle1 and matches[i]["player2"] == handle2) or ((matches[i]["player1"] == handle2 and matches[i]["player2"] == handle1))):
                rounds[curr_round-1]["matches"][i]["status"] = True
                rounds[curr_round-1]["matches"][i]["winner"] = win_handle
                a = math.floor(i/2)
                b = i%2
                rounds[curr_round]["matches"][a]["player" + str(b + 1)] = win_handle
                storage.update_one({"server": ctx.guild.id}, {"$set":{"storage": rounds}})
                break
            

        all_status = True
        for i in matches:
            if(i["status"] == False):
                all_status = False
        
        if(all_status):
            servers.update_one({"_id": ctx.guild.id},{"$set":{"current_round":curr_round + 1}})
 

    embed.set_author(name=botName)
    await text_channel.send(embed=embed)




@client.command()
async def showMatches(ctx):
    thisServer = servers.find_one({"_id": ctx.guild.id})
    curr_round = thisServer["current_round"]
    current_round_matches=storage.find_one({"server": ctx.guild.id})["storage"][curr_round - 1]["matches"]
    current_matchlist = current_matches.find_one({"server": ctx.guild.id})["matches"]

    embed=discord.Embed(
    title=f"Current Round : {curr_round} ",
    color=discord.Color.blue()
    )
    count=1
    for match in current_round_matches:
        
        id1 = match['player1']
        id2 = match['player2']

        disp = None
        if(match["status"] == False):
            match_={}
            flag = False
            for match in current_matchlist:
                if(match["id_s"]==[id1,id2] or match["id_s"]==[id2,id1]):
                    flag=True
                    match_=match
                    break
            if(flag):
                 current_time=time.ctime()[11:19]
                 hours=int(current_time[0:2])
                 minutes=int(current_time[3:5])
                 time_elapsed=(hours-match_["Start_Time"][0])*60+(minutes-match_["Start_Time"][1])
                 disp = f" status : ongoing ( {time_elapsed} mins left )"
            else:
                disp = " status : pending"

        elif(match["status"] == True):
            disp = " winner : " + match['winner']
        embed.add_field(name=f"{count}. {id1} vs {id2}\n",value=f"{disp}",  inline = False)
        count+=1
    await ctx.send(embed=embed)
    return

@client.command()
async def roundStatus(ctx,round: int):
    thisServer = servers.find_one({"_id": ctx.guild.id})
    text_channel_n = thisServer["text_channel"]
    global text_channel
    for x in ctx.guild.text_channels:
        if x.id == text_channel_n:
            text_channel = x

    rounds = storage.find_one({"server": ctx.guild.id})["storage"]
    matches = rounds[round-1]["matches"]
    embed = discord.Embed(
        title=f"Round {round} : ",
        color=discord.Color.dark_gold()
    )
    for i in range(len(matches)):
        if(matches[i]['status']==True):
            embed.add_field(
            name=matches[i]["player2"]+" vs "+matches[i]["player1"],
            value=f"Status: finished    Winner:{matches[i]['winner']}", inline=False)
        else:
            embed.add_field(
            name=matches[i]["player2"]+" vs "+matches[i]["player1"],
            value=f"Status: pending", inline=False)
    await ctx.send(embed=embed)


@client.command()
async def unregisterMe(ctx):
    thisServer = servers.find_one({"_id": ctx.guild.id})
    text_channel_n = thisServer["text_channel"]
    global text_channel
    for x in ctx.guild.text_channels:
        if x.id == text_channel_n:
            text_channel = x

    checkForStartTourney = matchesList.find_one({"server": ctx.guild.id})

    if checkForStartTourney is not None:
        embed = discord.Embed(
            title="Tournament Already Started",
            description="Tounament has already started so nothing can be changed.",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)
        return

    if thisServer["tourney_name"] == "--":
        embed = discord.Embed(
            title="No Tourney",
            description=f"{ctx.author.mention} there is no ongoing tournament.",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)
        return

    participantsListTemp = participantsList.find_one({"server": ctx.guild.id})


    found = False
    ix = 0
    for i in range(len(participantsListTemp["contestants"])):
        if participantsListTemp["contestants"][i]["id"] == ctx.author.id:
            found = True
            ix = i

    if found:
        participantsList.delete_one({"server": ctx.guild.id})
        participantsList.insert_one({"server": ctx.guild.id,
                                     "contestants": participantsListTemp["contestants"][:ix] + participantsListTemp[
                                         "contestants"][
                                         ix + 1:]})
        embed = discord.Embed(
            title="Unregistered",
            description=f"{ctx.author.mention} you are now unregistered.",
            color=discord.Color.gold()
        )
        embed.set_author(name=botName)
        await text_channel.send(embed=embed)
        return

    embed = discord.Embed(
        title="Couldn't Unregister",
        description=f"{ctx.author.mention} you are not part of any tournament right now.",
        color=discord.Color.gold()
    )
    embed.set_author(name=botName)
    await text_channel.send(embed=embed)



def match_builder(ctx):

    thisList = participantsList.find_one({"server": ctx.guild.id})

    player_list = []
    for i in thisList["contestants"]:
        player_list.append(i["cf_handle"])

    player_count = len(player_list)

    temp = ""
    for i in range(player_count):
        if(i == 0):
            temp += player_list[i]
        else:
            temp += ';'
            temp += player_list[i]
    uri = 'https://codeforces.com/api/user.info?handles=' + temp
    response_API = requests.get(uri)

    data = response_API.text
    parse_json = json.loads(data)
    player_list_updated = []
    for i in parse_json['result']:
        player_list_updated.append([i['rating'],i['handle']])
    player_list_updated.sort()
    rounds = int(math.log(player_count,2))
    rounds += 1
    storage_ = []
    for i in range(1,rounds+1):
        storage_element = {}
        if(i == 1):
            players = (player_count - 2**(rounds-1))*2
            if(players == 0):
                continue
            players_in_round = []
            for j in range(players):
                players_in_round.append(player_list_updated[j][1])
            matches = []
            for j in range(math.floor(players/2)):
                var = {}
                var['player1'] = players_in_round[2*j]
                var['player2'] = players_in_round[(2*j)+1]
                var['status'] = False
                var['winner'] = None
                matches.append(var)
            storage_element['matches'] = matches
            storage_.append(storage_element)
        elif(i == 2):
            players = 0
            if(len(storage_) != 0):
                players = len(storage_[0]['matches'])*2
            else:
                players = 0
            players_in_round = []
            for j in range(math.floor(players/2)):
                players_in_round.append('qualifier_' + str(j+1))
            for j in range(players,player_count):
                players_in_round.append(player_list_updated[j][1])
            players = len(players_in_round)
            matches = []
            for j in range(math.floor(players/2)):
                var = {}
                var['player1'] = players_in_round[2*j]
                var['player2'] = players_in_round[(2*j)+1]
                var['status'] = False
                var['winner'] = None
                matches.append(var)
            storage_element['matches'] = matches
            storage_.append(storage_element)
        else:
            players = int(2**(rounds + 1 - i))
            players_in_round = []
            for j in range(players):
                players_in_round.append('seed_' + str(j+1))
            matches = []
            for j in range(math.floor(players/2)):
                var = {}
                var['player1'] = players_in_round[2*j]
                var['player2'] = players_in_round[(2*j)+1]
                var['status'] = False
                var['winner'] = None
                matches.append(var)
            storage_element['matches'] = matches
            storage_.append(storage_element)

    servers.update_one({"_id": ctx.guild.id},{"$set":{"current_round": 1}})
    storage.update_one({"server": ctx.guild.id},{"$set":{"storage": storage_}})


def unsolved_checker(contest_id, p_index, handle):
    if(len(p_index) > 1):
        return False
    problem_index = ord(p_index) - ord("A")
    uri = "https://codeforces.com/api/contest.standings?contestId="+str(contest_id)+"&from=1&count=5&showUnofficial=true&handles=" + handle

    response_API = requests.get(uri)
    # print(response_API.status_code)
    data = response_API.text
    parse_json = json.loads(data)['result']['rows']

    if(len(parse_json) == 0):
        return True
    else:
        points = parse_json[0]['problemResults'][problem_index]['points']
        rejected_attempt = parse_json[0]['problemResults'][problem_index]['rejectedAttemptCount']


        if(points > 0 or rejected_attempt > 0):
            return False
        else:
            return True

client.run(token)