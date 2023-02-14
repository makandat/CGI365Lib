# CGI365Lib.py について
このモジュールは、Python3 で書かれている CGI を作るのを簡単にするためのモジュールである。
CGI365Lib.py には次の2つのクラスとモジュール関数が含まれている。
* Request
* Response

# サンプル
次の例はパラメータ message で受け取った文字列をそのまま返す CGI である。
```python:echo.cgi
#!/usr/bin/env python3
#  echo.cgi
import CGI365Lib as CGI

#CGI.LOG = "/var/www/data/echo.log"
CGI.info('echo.cgi')
request = CGI.Request()
response = CGI.Response()
message = request.getParam('message')
CGI.info(message)
response.sendSimple(message)
```