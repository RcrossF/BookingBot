# BookingBot
Books UVIC study rooms.

Edit the json files with correct information before running. Slack api is optional as room_snag.py can be used for basic room booking from the command line

TODO:
  - If a time slot cannot be booked continuously in one room try and book multiple shorter slots in other rooms
  - Support multiple netlinkIDs for longer bookings (Max 2hr/day/ID)
  - Store netlinkIDs in something other than plaintext
  - Improve slack commands
