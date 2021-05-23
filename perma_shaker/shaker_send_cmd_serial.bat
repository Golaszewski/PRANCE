@echo on
taskkill /f /im putty.exe
taskkill /f /im plink.exe
cmd.exe /C "start cmd.exe /C C:\Users\Hamilton\Dropbox\Hamilton_Methods\perma_shaker\shaker_serial.bat %1"
PING 1.1.1.1 -n 2 -w 600 >NUL
taskkill /f /im plink.exe
exit