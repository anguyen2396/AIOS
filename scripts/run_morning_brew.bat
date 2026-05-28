@echo off
cd /d "C:\Users\Administrator\Desktop\AIOS"
claude --print "Run /morning-brew — read Obsidian action items from C:\Users\Administrator\Desktop\austin-brain\Daily Notes\, sync to Google Calendar, generate daily brief, send HTML email via scripts/send_morning_brew.py to austinngg996@gmail.com" >> logs\morning-brew.log 2>&1
