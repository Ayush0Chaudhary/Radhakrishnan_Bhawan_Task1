# drone-ps

## Installation
Require python>=3.6
'''
pip install -r requirements.txt
'''


## Executables
To run as standalone application
## .app in macOS
```
pip install pyinstaller==5.1
```

You need to add a logo for your application. Replace 0.jpg with the path of your logo.

```
pyinstaller --add-data '0.jpg:.' app.py
pyinstaller app.spec
```
```
mkdir appfolder
```
* Copy all the contents of dist/app/ and paste it to appfolder
* Rename appfolder to **app.app**

## .exe in Windows
```
pip install pyinstaller
```
Use pyinstaller to convert into .exe :
```
pyinstaller --onefile --windows --icon=logo.ico app.py
