import os
import discord
import logging
import asyncio
import sqlite3
import textwrap
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class Devy:
    def __init__(self):
        self.client = discord.Client(intents=discord.Intents.default())
        self.handler = self.init_logging()
        self._DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        self._CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
        self._SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
        self.SLEEP_TIME = 300 # 5 minutes
        self.conn = sqlite3.connect('projects.db')
        self.df = pd.read_csv(
            "https://docs.google.com/spreadsheets/d/e/"
            f"{self._SPREADSHEET_ID}/pub?output=csv"
        )
        
        print("Client initialized")

        @self.client.event
        async def on_ready():
            """Event triggered when the bot is ready."""
            logging.info(f'Logged in as {self.client.user}')
            projects = self.df.loc[~self.df['ID'].isnull()]
            projects.to_sql('projects', self.conn, if_exists='replace', index=False)
            self.conn.commit()

            while True:
                await self.check()
                await asyncio.sleep(self.SLEEP_TIME)

    def init_logging(self):
        """Initialize logging for the bot."""
        handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        handler.setLevel(logging.INFO)

        return handler

    def run(self):
        """Start the Discord bot and connect to Discord API."""
        print("Starting the bot...")
        self.client.run(token=self._DISCORD_TOKEN, reconnect=True, log_handler=self.handler)

    async def send_notification(self, new_projects):
        """Send a notification about new projects to the Discord channel."""

        print("Sending notification...")
        channel = self.client.get_channel(int(self._CHANNEL_ID))
        if channel:
            embeds = []
            for _, row in new_projects.iterrows():
                desc = textwrap.fill(row["Project Description"], width=100)
                e = discord.Embed(
                    title=f"{row['ID']} — {row['Project Name'] or 'TBA'}",
                    description=desc[:2048],
                    color=discord.Color.blue()
                )
                e.add_field(name="Supervisor", value=row["Supervisor Name"] or "TBA", inline=True)
                e.add_field(name="Date",       value=row["Project_Date"]    or "N/A",  inline=True)
                embeds.append(e)

            for embed in embeds:
                await channel.send(embed=embed)
            print("Notification about new projects sent.")
        else:
            print("Channel not found.")
    
    async def check(self):
        """Check for new projects in the Google Sheet and send notifications."""

        print("Checking for new projects...")
        self.df = pd.read_csv(
            "https://docs.google.com/spreadsheets/d/e/"
            f"{self._SPREADSHEET_ID}/pub?output=csv"
        )

        projects = self.df.loc[~self.df['ID'].isnull()]

        db = pd.read_sql('SELECT * FROM projects', self.conn)
        curr_projects = db.loc[~db['ID'].isnull()]
        new_projects = projects[~projects['ID'].isin(curr_projects['ID'])]

        if not new_projects.empty:
            new_projects.to_sql('projects', self.conn, if_exists='append', index=False)
            self.conn.commit()
            print("New projects added to the database.")
            await self.send_notification(new_projects)
        else:
            print("No new projects found.")

if __name__ == "__main__":
    devy = Devy()
    devy.run()
