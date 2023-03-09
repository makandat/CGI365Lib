# CGI365Lib.py について
このモジュールは、Python3 で書かれている CGI を作るのを簡単にするためのモジュールである。
CGI365Lib.py には次の 3 つのクラスとモジュール関数が含まれている。
* Request
* Response
* Utility
* その他

# サンプル
次の例はパラメータ message で受け取った文字列をそのまま返す CGI である。
```python:echo.cgi
#!/usr/bin/env python3
#  echo.cgi
import CGI365Lib as CGI

request = CGI.Request()
response = CGI.Response()
message = request.getParam('message')
response.sendSimple(message, charset="utf-8")
```

# 文書
* [index.html](index.html)
* [request.html](request.html)
* [response.html](response.html)
* [utility.html](utility.html)
* [debug.html](debug.html)
