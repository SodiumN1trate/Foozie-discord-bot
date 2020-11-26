#Foozie discord bot import discord
import discord
from config import *
from discord.ext import commands
import re
from discord import Permissions
import pytz
from threading import Timer
from datetime import datetime

#Make request to databse every 1h
def Request():
    sql = ("SELECT * FROM `logic_botinfo`")
    cursor.execute(sql)
    print("Made request to database.")
    timer = Timer(3600.0, Request)
    timer.start()


timer = Timer(3600.0, Request)
timer.start()


#Make mute/ warn embeds
def mute_messages(message, warns, ServersAllowedWarns):
    if warns:
        Embed = discord.Embed(
            title="Brīdinājums!",
            description="{0}\nTiek brīdināts par aizliegto vārdu lietošanu: {1}/{2}!\n-Foozie".format(
                message.author.mention, warns, ServersAllowedWarns),
            timestamp=datetime.utcnow().replace(tzinfo=pytz.utc),
            colour=discord.Colour.purple()
        )
        status = {'success': 'Warn', 'Embeds': Embed}
        #If warns are equivalent with servers allowed warns then give warn
        if warns >= ServersAllowedWarns:
            sql = ("UPDATE `warn_logs` SET `warns` = 0, `Mute` = 1 WHERE `Discord id` = {0} AND `Discord server id` = {1};".format(
                message.author.id, message.guild.id))
            cursor.execute(sql)
            sql = (
                "UPDATE `logic_botinfo` SET `WarnNum` = `WarnNum`+ 1 WHERE `id` = 1;")
            cursor.execute(sql)
            conn.commit()
            Embed = discord.Embed(
                title="Noklusinājums!",
                description="{0}\nTika noklusināts par servera noteikumu neivērošanu!\n-Foozie".format(
                    message.author.mention),
                timestamp=datetime.utcnow().replace(tzinfo=pytz.utc),
                colour=discord.Colour.purple()
                )
            status = {'success': 'Mute', 'Embeds': Embed}
            return status
        return status
    #If user aren't in mute list then insert the user in warn list and set+1 warn
    else:
        Embed = discord.Embed(
            title="Brīdinājums!",
            description="{0}\n Tiek brīdināts par aizliegto vārdu lietošanu!".format(
                message.author.mention),
            timestamp=datetime.utcnow().replace(tzinfo=pytz.utc),
            colour=discord.Colour.purple()
        )
        status = {'success': 'FirstWarn', 'Embeds': Embed}
        return status


clientBot = discord.Client()
client = commands.Bot(command_prefix='$')

#Remove basic help command
client.remove_command('help')


#SQL injection avoid
def CheckOnWrongSymbols(text):
    FormatedText = re.sub(";|\\|'|:|\"|/", "", str(text))
    try:
        if '\\' in FormatedText[len(FormatedText)-1]:
            FormatedText = FormatedText.replace(
                FormatedText[len(FormatedText)-1], ' ')
    except:
        pass
    return FormatedText


#Bot login status
@client.event
async def on_ready():
    print("Discord bot: {0.user} succesfully loged!".format(client))
    await client.change_presence(activity=discord.Game(name='$help'))

#If bot joined in new guild
@client.event
async def on_guild_join(guild):
    GuildId = guild.id
    GuildName = CheckOnWrongSymbols(guild)
    sql = ("UPDATE `logic_botinfo` SET `ServersNum` = `ServersNum` + 1 WHERE `id` = '1'")
    cursor.execute(sql)
    cursor.execute("INSERT INTO `discord_servers_info` (`ServerName`, `BadWords`, `server_id`) VALUES ('{0}', '', {1});".format(GuildName, GuildId))
    conn.commit()
    print("{0.user} joined in new guild/server: ".format(client) + GuildName)
    role = await guild.create_role(name='[ Muted by Foozie ]', permissions=Permissions(read_messages=True))

#When bot got removed from server
@client.event
async def on_guild_remove(guild):
    sql = ("UPDATE `logic_botinfo` SET `ServersNum` = `ServersNum` - 1 WHERE `id` = '1'")
    cursor.execute(sql)
    cursor.execute("DELETE FROM `discord_servers_info` WHERE `server_id` = {0};".format(guild.id))
    cursor.execute('DELETE FROM `warn_logs` WHERE `Discord server id`={0}'.format(guild.id))
    conn.commit()


#Do something with user if that said bad word
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    sql = ("SELECT `Toggle reader` FROM `discord_servers_info` WHERE `server_id` = {0}".format(message.guild.id))
    cursor.execute(sql)
    GottedPosition = cursor.fetchone()
    for Possition in GottedPosition[0]:
        if Possition == "1":
            if message.author.id != message.guild.owner_id:
                cursor.execute("SELECT `BadWords` FROM `discord_servers_info` WHERE `server_id` = {0};".format(message.guild.id))
                BadWords = cursor.fetchall()
                for z in BadWords:
                    z = ''.join(z)
                    #If user typed Bad word
                    if z.upper() in message.content.upper():
                        #There we got servers warn points
                        sql = "SELECT `warn points` FROM `discord_servers_info` WHERE `server_id` = {0};".format(
                            message.guild.id)
                        cursor.execute(sql)
                        ServersAllowedWarns = list(cursor.fetchone())
                        #There we got user warn points
                        sql = "SELECT `warns` FROM `warn_logs` WHERE `Discord id` = {0} AND `Discord server id` = {1};".format(
                            message.author.id, message.guild.id)
                        cursor.execute(sql)
                        warns = cursor.fetchone()
                        #Check if user already have warn
                        if warns == None:
                            cursor.execute("INSERT INTO `warn_logs` (`Discord username`, `Discord id`, `Discord server id`) VALUES ('{0}', {1}, {2})".format(message.author.name, message.author.id, message.guild.id))
                            conn.commit()
                            sql = "SELECT `warns` FROM `warn_logs` WHERE `Discord id` = {0} AND `Discord server id` = {1};".format(
                                message.author.id, message.guild.id)
                            cursor.execute(sql)
                            warns = cursor.fetchone()
                        #Add +1 warn
                        sql = ("UPDATE `warn_logs` SET `warns` = `warns` + 1 WHERE `Discord id` = {0} AND `Discord server id` = {1};".format(
                            message.author.id, message.guild.id))
                        cursor.execute(sql)
                        conn.commit()
                        #User notification
                        Status = mute_messages(message, warns[0], ServersAllowedWarns[0])
                        await message.channel.send(embed=Status['Embeds'])
                        if Status['success'] == 'Mute':
                            await message.channel.set_permissions(message.author, read_messages=True,send_messages=False)
                            print(message.author , "was muted!")

    await client.process_commands(message)
                        


#Command which add list of bad words
@client.command()
async def bad_words_set(ctx, *args):
    if ctx.author.id == ctx.guild.owner_id:
        BadWords = ' '.join(args)
        BadWordsCheck = CheckOnWrongSymbols(BadWords)
        BadWordsList = list(args)
        if BadWordsCheck == '':
            await ctx.send("Drīkst rakstīt tikai vārdus un ciparus!")
            return
        for x in BadWordsList:
            BadWordsList.remove(x)
            GottedNummber = BadWordsList.count(x.upper())
            if GottedNummber >= 1:
                await ctx.send("Vārdi nedrīkst atkārtoties!")
                return
        else:
            sql = ("UPDATE `discord_servers_info` SET `BadWords` = '{0}' WHERE `server_id` = {1};".format(
                BadWordsCheck, ctx.guild.id))
            cursor.execute(sql)
            conn.commit()
            await ctx.send("Tika uzstādīts jauns aizliegto vārdu saraksts!")
    else:
        await ctx.send("Tikai grupas īpašnieks var veikt izmaiņas!")


#Command which set allowed warns on server
@client.command()
async def warn_points_set(ctx, warnpoints):
    if ctx.author.id == ctx.guild.owner_id:
        GottedNummber = CheckOnWrongSymbols(warnpoints)
        CheckOnString = re.sub('[A-Z a-z]', '', GottedNummber)
        if CheckOnString == '':
            await ctx.send("Drīkst rakstīt tikai ciparus!")
            return
        sql = ("UPDATE `discord_servers_info` SET `Warn points` = {0} WHERE `server_id` = {1};".format(warnpoints, ctx.guild.id))
        cursor.execute(sql)
        conn.commit()
        await ctx.send("Servera brīdinājuma punktu atļautais daudzmums tika nomainīts uz: {0}".format(warnpoints))
    else:
        await ctx.send("Tikai grupas īpašnieks var veikt izmaiņas!")


#Show list of bad words
@client.command()
async def bad_words_list(ctx):
    cursor.execute(
        "SELECT `BadWords` FROM `discord_servers_info` WHERE `server_id` = {0};".format(ctx.guild.id))
    BadWords = cursor.fetchall()
    for x in BadWords[0]:
        pass
    BadWordList = x.split()
    BadWordListSplit = ', '.join(BadWordList)
    if BadWordListSplit == '':
        await ctx.send("Nav uzstādīti aizliegtie vārdi!")
    else:
        await ctx.send("Aizliegtie vārdi: \"" + BadWordListSplit + "\"")


#Ban from guild command
@client.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    print(ctx.author.id)
    print(ctx.guild.owner_id)
    if ctx.author.id == ctx.guild.owner_id:   
        try:
            sql = ("UPDATE `logic_botinfo` SET `BlockedNum` = `BlockedNum`+ 1 WHERE `id` = 1;")
            cursor.execute(sql)
            conn.commit()
            await ctx.guild.ban(user=member, reason=reason, delete_message_days=7)
            Embeds = discord.Embed(
                title="Bloķēts!",
                description="{0} nobloķēja {1}. Iemesls: {2}!".format(
                    ctx.author.mention, member.mention, reason),
                timestamp=datetime.utcnow().replace(tzinfo=pytz.utc),
                colour=discord.Colour.purple()
            )
            await ctx.send(embed=Embeds)
        except:
            await ctx.send("Nav atrasts tāds lietotājs!")
    else:
        await ctx.send("Tikai grupas īpašnieks var veikt izmaiņas!")        


#Kick from guild command
@client.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    print(member)
    print(member.id)
    if ctx.author.id == ctx.guild.owner_id:
        try:
            sql = ("UPDATE `logic_botinfo` SET `KickedNum` = `KickedNum`+ 1 WHERE `id` = 1;")
            cursor.execute(sql)
            await member.kick(reason=reason)
            conn.commit()
            Embeds = discord.Embed(
                title="Izmests!",
                description="{0} izmeta {1}. Iemesls: {2}".format(
                    ctx.author.mention, member.mention, reason),
                timestamp=datetime.utcnow().replace(tzinfo=pytz.utc),
                colour=discord.Colour.purple()
            )
            await ctx.send(embed=Embeds)
        except:
            await ctx.send("Nav atrasts tāds lietotājs!")
    else:
        await ctx.send("Tikai grupas īpašnieks var veikt izmaiņas!")    

#Update bad words list
@client.command()
async def bad_words_update(ctx, *args):
    if ctx.author.id == ctx.guild.owner_id:
        BadWords = ' '.join(args)
        BadWordsCheck = CheckOnWrongSymbols(BadWords)
        BadWordsList = list(args)
        if BadWordsCheck == '':
            await ctx.send("Drīkst rakstīt tikai vārdus un ciparus!")
            return
        for x in BadWordsList:
            print(x)
            BadWordsList.remove(x)
            GottedNummber = BadWordsList.count(x)
            if GottedNummber >= 1:
                await ctx.send("Vārdi nedrīkst atkārtoties!")
                return
        else:
            sql = ("SELECT `BadWords` FROM `discord_servers_info` WHERE `server_id` = {0}".format(
                ctx.guild.id))
            cursor.execute(sql)
            BadWords = cursor.fetchall()
            for x in BadWords[0]:
                pass
            BadWordList = x.split()
            BadWordListSplit = ' '.join(BadWordList)
            BadWords = BadWordListSplit + ' ' + BadWordsCheck
            sql = ("UPDATE `discord_servers_info` SET `BadWords` = '{0}' WHERE `server_id` = {1};".format(
                BadWords, ctx.guild.id))
            cursor.execute(sql)
            conn.commit()
            await ctx.send("Tika pievienoti jauni vārdi vārdu saraksts!")
    else:
        await ctx.send("Tikai grupas īpašnieks var veikt izmaiņas!")

#Toggle reader.
@client.command() 
async def toggle_reader(ctx):
    if ctx.author.id == ctx.guild.owner_id:
        sql = ("SELECT `Toggle reader` FROM `discord_servers_info` WHERE `server_id` = {0}".format(ctx.guild.id))
        cursor.execute(sql)
        GottedPosition = cursor.fetchone()
        for Position in GottedPosition:
            if Position == "0" or Position == "2":
                sql = ("UPDATE `discord_servers_info` SET `Toggle reader` = '1' WHERE `server_id` = {0}".format(ctx.guild.id))
                cursor.execute(sql)
                conn.commit()
                await ctx.send("Tika ieslēgts lasīšanas režīms!")
            if Position == "1":
                sql = ("UPDATE `discord_servers_info` SET `Toggle reader` = '0' WHERE `server_id` = {0}".format(ctx.guild.id))
                cursor.execute(sql)
                conn.commit()
                await ctx.send("Tika izslēgts lasīšanas režīms!")
    else:
        await ctx.send("Tikai grupas īpašnieks var veikt izmaiņas!")


#Help command
@client.command()
async def help(ctx):
    Embeds = discord.Embed(
        title='Palīdzība.',
        timestamp=datetime.utcnow().replace(tzinfo=pytz.utc),
        colour=discord.Colour.purple()
    )
    Embeds.add_field(name='Komandas var apskatīties mājaslapā.', value='http://foozie.ddns.net/commands', inline=False)
    await ctx.send(embed=Embeds)

#Mute command
@client.command()
async def mute(ctx, member: discord.Member, *, reason=None):
    if ctx.author.id == ctx.guild.owner_id:
        try:
            Embeds = discord.Embed(
                title="Noklusinājums!",
                description="{0} noklusināja {1}. Iemesls: {2}".format(
                    ctx.author.mention, member.mention, reason),
                timestamp=datetime.utcnow().replace(tzinfo=pytz.utc),
                colour=discord.Colour.purple()
            )
            await ctx.send(embed=Embeds)
            await ctx.channel.set_permissions(message.author, read_messages=True,send_messages=False)
            print(ctx.author, "was muted!")
        except:
            await ctx.send("Nav atrasts tāds lietotājs!")
    else:
        await ctx.send("Tikai grupas īpašnieks var veikt izmaiņas!")

#Unmute command
@client.command()
async def unmute(ctx, member: discord.Member):
    if ctx.author.id == ctx.guild.owner_id:
        try:
            Embeds = discord.Embed(
                title="Noņemts noklusinājums!",
                description="{0} noņēma noklusinājumu {1}".format(
                    ctx.author.mention, member.mention),
                timestamp=datetime.utcnow().replace(tzinfo=pytz.utc),
                colour=discord.Colour.purple()
            )
            await ctx.send(embed=Embeds)
            await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
        except:
            await ctx.send("Nav atrasts tāds lietotājs!")
    else:
        await ctx.send("Tikai grupas īpašnieks var veikt izmaiņas!")


client.run(TOKEN)
