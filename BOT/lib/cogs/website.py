"""
    File: /lib/cogs/website.py
    Info: This cog handles the website which talks to the API.
"""
from datetime import datetime
from math import prod
import nextcord
from nextcord.ext.commands import Cog, command
from nextcord.ext.commands.core import Command
from nextcord import Embed, Colour, colour
from quart import Quart, request
from ..utils.database import db
from ..utils.api import *
from ..utils.util import require_apikey
from bson.json_util import ObjectId, dumps
from ro_py import Client
import json
import string
import random
import requests

app = Quart(__name__)

# Had to do this cause I cant pass in self in quart
with open("./BOT/lib/bot/config.json") as config_file:
    config = json.load(config_file)
roblox = Client()
verificationkeys = {}

# Define Functions

## This needs to be done with the MongoDB database to make sure the _id is a string and not ObjectId
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MyEncoder, self).default(obj)


app.json_encoder = MyEncoder

# Website Handling


@app.route("/", methods=["GET"])
async def index():
    return {"message": "Ok"}


@app.route("/v1/status", methods=["GET"])
async def status():
    result = db.command("serverStatus")
    if result:
        return {"message": "Ok", "info": {"api": "Ok", "database": "Ok"}}
    else:
        return {"message": "Ok", "info": {"api": "Ok", "database": "Error"}}


@app.route("/v1/products", methods=["GET"])
async def products():
    dbresponse = getproducts()
    results = {}
    for i in dbresponse:
        results[i["name"]] = i
    return results


@app.route("/v1/create_product", methods=["POST"])
@require_apikey
async def create_product():
    info = await request.get_json()
    try:
        createproduct(info["name"], info["description"], info["price"])
        return {
            "info": {
                "name": info["name"],
                "description": info["description"],
                "price": info["price"],
            }
        }
    except:
        return {"errors": [{"message": "Unable to delete product"}]}


@app.route("/v1/update_product", methods=["POST"])
@require_apikey
async def update_product():
    info = await request.get_json()
    try:
        updateproduct(
            info["oldname"], info["newname"], info["description"], info["price"]
        )
        return {
            "info": {
                "name": info["newname"],
                "description": info["description"],
                "price": info["price"],
            }
        }
    except:
        return {"errors": [{"message": "Unable to update product"}]}


@app.route("/v1/delete_product", methods=["DELETE"])
@require_apikey
async def delete_product():
    info = await request.get_json()
    try:
        deleteproduct(info["name"])
        return {"message": "Deleted"}
    except:
        return {"errors": [{"message": "Unable to create product"}]}


@app.route("/v1/user", methods=["GET"])
async def get_user():
    info = await request.get_json()
    dbresponse = getuser(info["userid"])
    return dumps(dbresponse)[1:-1]


@app.route("/v1/verify_user", methods=["POST"])
@require_apikey
async def verify_user():
    info = await request.get_json()
    user = getuser(info["userid"])
    if not user:
        key = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        verificationkeys[key] = info["userid"]
        return {"key": key}
    else:
        return {"errors": [{"message": "User is already verified"}]}


@app.route("/v1/give_product", methods=["POST"])
@require_apikey
async def give_product():
    info = await request.get_json()
    try:
        giveproduct(info["userid"], info["productname"])
        userinfo = getuser(info["userid"])
        return dumps(userinfo)[1:-1]
    except:
        return {"errors": [{"message": "Unable to give product"}]}


@app.route("/v1/revoke_product", methods=["DELETE"])
@require_apikey
async def revoke_product():
    info = await request.get_json()
    try:
        revokeproduct(info["userid"], info["productname"])
        userinfo = getuser(info["userid"])
        return dumps(userinfo)[1:-1]
    except:
        return {"errors": [{"message": "Unable to revoke product"}]}


@app.route("/v1/create_purchase", methods=["POST"])
@require_apikey
async def create_purchase():
    ## TODO: Finish and test
    return # Do this for now because it will cause a build and test error
    info = await request.get_json()
    if info and info["gameid"] and info["name"] and info["price"]:
        data = [info["gameid"], info["name"], info["price"], info["name"] + " " + info["price"]]
        cookies = {".ROBLOSECURITY": config["Roblox"]["Cookie"]}
        request = requests.post("https://www.roblox.com/places/developerproducts/add", data=data, cookies=cookies)
        
        if request.status_code == 200:
            pass


# Bot Handling


class Website(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(
        name="website",
        aliases=["web", "ws", "websitestatus"],
        brief="Displays if the website is online.",
        catagory="misc",
    )
    async def website(self, ctx):
        if ctx.message.author.id in self.bot.owner_ids:
            await ctx.send("🟢 Website Online")

    @command(name="verify", brief="Verify's you as a user.", catagory="user")
    async def verify(self, ctx, key):
        if key in verificationkeys:
            userid = verificationkeys[key]
            try:
                user = await roblox.get_user(userid)
                username = user.name
                verifyuser(userid, ctx.author.id, username)
                verificationkeys.pop(key)
                await ctx.send("Verified", delete_after=5.0, reference=ctx.message)
            except:
                await ctx.send(
                    "I was unable to verify you",
                    delete_after=5.0,
                    reference=ctx.message,
                )
        else:
            await ctx.send(
                "The provided key was incorrect please check the key and try again.",
                delete_after=5.0,
                reference=ctx.message,
            )

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("website")
            await self.bot.stdout.send("`/lib/cogs/website.py` ready")
            print(" /lib/cogs/website.py ready")


def setup(bot):
    bot.loop.create_task(
        app.run_task("0.0.0.0")
    )  # It is highly recomended that you change "0.0.0.0" to your server IP in a production env
    bot.add_cog(Website(bot))
