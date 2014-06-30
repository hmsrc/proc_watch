A simple python script to check if processes running exceed a set cpu/memory value, and terminates them.
Create a cron job to run the script periodically.  If the process is there twice in a row, it's terminated, and an email send to the user.
The INI file includes the body of the message and the from and reply to, as well the thresholds, processes that can be excluded, and high/low UID values.




    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
