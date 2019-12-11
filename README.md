# BookingBot
Books UVIC study rooms.

Edit the json files with correct information before running (Passwords base64 encoded). Add or remove as many users as you like. Slack api is optional as room_snag.py can be used for basic room booking from the command line

TODO:
  - Improve slack commands
  
  Below should be fixed in V2 coming soon...
  - Check existing bookings through the bot
  - Improve multi netlink booking functionality, some times will be double booked if the user switches over
  - Switch from lxml to beautifulSoup
