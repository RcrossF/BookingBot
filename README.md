# BookingBot
Books UVIC study rooms.

Edit the json files with correct information before running (Passwords base64 encoded). Slack api is optional as room_snag.py can be used for basic room booking from the command line

TODO:
  - DONE If a time slot cannot be booked continuously in one room try and book multiple shorter slots in other rooms
  - DONE(?) If time is already booked on a day and another booking is attempted on the same day that would cause the total time to be >2hr then book part of the requested time up to 2hrs
  - DONE Support multiple netlinkIDs for longer bookings (Max 2hr/day/ID)
  - DONE Store netlinkIDs in something other than plaintext
  - Improve slack commands
  - Check existing bookings through the bot
  - Improve multi netlink booking functionality, some times will be double booked if the user switches over
