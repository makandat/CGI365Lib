# CGI356Lib.py v1.2.1  2023-02-14
import os, sys, datetime, io, re
import urllib.parse
import pathlib
import json
from pprint import pprint

# 文字コード
ENC = 'utf-8'
# デバッグ用ログファイル
LOG = ""

# デバッグ用 判別
def isDebug():
  return len(sys.argv) > 1 and sys.argv[1] == "debug"

# デバッグ用 QUERY_STRING 設定
def setQueryString(qs):
  if isDebug():
    os.environ["QUERY_STRING"] = qs

# デバッグ用 HTTP_COOKIE 設定
def setHttpCookie(cookie):
  if isDebug():
    os.environ["HTTP_COOKIE"] = cookie

# デバッグ用 REQUEST_METHOD 設定
def setRequestMethod(method):
  if isDebug():
    os.environ["REQUEST_METHOD"] = method

# デバッグ用ログ出力
def info(obj):
  if LOG == "":
    return
  now = datetime.datetime.now()
  strnow = now.isoformat()
  with open(LOG, mode="at") as f:
    f.write(strnow + " " + str(obj) + "\n")

# Request class
class Request:
  def __init__(self):
    # Windows の場合はデフォルトの文字コードが Shift JIS なので、これがないと文字化けする。
    if os.name == 'nt':
      sys.stdin= io.TextIOWrapper(sys.stdin.buffer, encoding=ENC)
    self.RawData = ""                 #  受け取った生データ
    self.Query = self._getQuery()     # GET パラメータ 辞書
    self.Form = self._getForm()       # POST パラメータ 辞書
    self.Method = self._getMethod()   # HTTP メソッド 'GET', 'POST'...
    self.Address = self._getAddress() # アドレス 辞書 キーは 'Server', 'Client', 'Host'
    self.Cookie = self._getCookie()   # クッキー 辞書
    return

  # CGI パラメータを得る。キーが存在しないときは空白を返す。
  def getParam(self, key):
    if key in self.Query:
      return self.Query[key]
    elif key in self.Form:
      return self.Form[key]
    else:
      return ""

  # b'...' を複数行文字列に変換
  def btos(self, bstr=""):
    if bstr == "":
      bstr = self.RawData
    if bstr.startswith("b'"):
      bstr = bstr[2:].strip("'")
      bstr = bstr.replace("\\n", "\n").replace("\\\\", "\\")
    else:
      pass
    return bstr

  # FormData 文字列から変数名をキーとする辞書を作成する。
  def parseFormData(self, s=""):
    name =""
    result = dict()
    if s == "":
      s = self.RawData
    lines = s.split("\\r\\n")
    for line in lines:
      if line.startswith("b'-----") or line.startswith("-----") or line == "":
        pass
      elif "name=" in line:
        m = line.split("name=\"")
        m2 = m[1].split("\"")
        name = m2[0]
      else:
        if line != "'":
          value = line
          result[name] = line
    return result

  # クライアントから受け取った生データ文字列をJSON形式とみなし変数名をキーとする辞書を作成する。
  def parseJSON(self, s=""):
    result = dict()
    if s == "":
      s = self.RawData
    s = self.btos(s)
    obj = json.loads(s)
    return obj

  # %xx 文字を元の文字に戻す。
  def fromPercent(self, ps="", plus=True):
    if ps == "":
      ps = self.RawData
    if plus:
      return urllib.parse.unquote_plus(ps)
    else:
      return urllib.parse.unquote(ps)

  # ASCII 文字以外の文字や URL の特殊文字を %xx に変換する。
  def toPercent(self, s, plus=True):
    if plus:
      return urllib.parse.quote_plus(ps)
    else:
      return urllib.parse.quote(ps)

  # 環境変数 QUERY_STRING から変数名をキーとする辞書を作成する。
  def _getQuery(self):
    result = dict()
    try:
      qs = os.environ["QUERY_STRING"]
      if isDebug() and qs != "":
        self.Method = "GET"
      self.RawData = qs
      params = urllib.parse.parse_qs(qs)
      for key in params:
        result[key] = params[key][0]
    except Exception as e:
      pass
    return result

  # 標準入力から変数名をキーとする辞書を作成する。
  def _getForm(self):
    result = dict()
    try:
      if isDebug():
        print("Enter form data > ")
        self.Method = 'POST'
      s = str(sys.stdin.buffer.read())
      self.RawData += s
      #info(s)
      if s.startswith("b'-----"):
        # FormData
        result = self.parseFormData(s)
      else:
        # その他
        result = urllib.parse.parse_qs(s)
        for key in ps:
          result[key] = ps[key][0]
    except Exception as e:
      pass
    return result

  # 環境変数 REQUEST_METHOD から HTTP メソッド名を返す。
  def _getMethod(self):
    method = "GET"
    try:
      if isDebug() == False:
        method = os.environ["REQUEST_METHOD"]
      else:
        if self.Method != "":
          method = self.Method
    except:
      method = ""
    return method

  # 環境変数 HTTP_COOKIE からクッキー名をキーとする辞書を返す。
  def _getCookie(self):
    cookies = dict()
    try:
      http_cookie = os.environ["HTTP_COOKIE"]
      cookielist = http_cookie.split('; ')
      for item in cookielist:
        kv = item.split('=')
        k = kv[0]
        v = kv[1]
        cookies[k] = v
    except:
      pass
    return cookies

  # 環境変数から self.Address の内容を作成する。
  def _getAddress(self):
    address = dict()
    try:
      address['Server'] = os.environ["SERVER_ADDR"] + ":" + os.environ["SERVER_PORT"]
      address['Client'] = os.environ["REMOTE_ADDR"] + ":" + os.environ["REMOTE_PORT"]
      address['Host'] = os.environ["HTTP_HOST"]
    except:
      pass
    return address


# Response class
class Response:
  def __init__(self):
    # Windows の場合はデフォルトの文字コードが Shift JIS なので、これがないと文字化けする。
    if os.name == 'nt':
      sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=ENC)
    self.Cookie = list()
    return

  # クッキーをセットする。cookies は辞書オブジェクト。
  def setCookie(self, cookies):
    for key, value in cookies.items():
      self.Cookie.append(f"{key}={value}")
    return

  # Set-Cookie: を作成する。
  def makeCookie(self):
    if len(self.Cookie) == 0:
      return ""
    buff = ""
    for s in self.Cookie:
      buff += f"Set-Cookie: {s}\n"
    return buff

  # 文字列を応答として返す。s はその文字列。
  def sendString(self, s, mime=f'text/html; charset={ENC}', cookie=True, embed=None):
    if isinstance(embed, dict):
      for k, v in embed.items():
         s = s.replace("{{" + k + "}}", v)
    buff = ""
    if mime == "text":
      mime = f"Content-Type: text/plain; charset={ENC}"
    elif mime == "html":
      mime = f"Content-Type: text/html; charset={ENC}"
    elif mime == "json":
      mime = f"Content-Type: applicayion/json; charset={ENC}"
    elif mime == "xml":
      mime = f"Content-Type: applicayion/xml; charset={ENC}"
    elif mime == "svg":
      mime = f"Content-Type: image/svg+xml; charset={ENC}"
    else:
      pass
    if cookie:
      buff = self.makeCookie()
    buff += mime + "\n\n" + s
    print(buff)
    return

  # 単純な文字列を返す。
  def sendSimple(self, s):
    print("Content-Type: text/plain\n\n" + s)
    return

  # バイナリーデータを返す。
  def sendBinData(self, data):
    print(b"Content-Type: application/octet-stream\n")
    sys.stdout.buffer.write(data)
    return

  # データを JSON に変換し応答として返す。
  def sendJSON(self, data, mime=f'application/json; charset={ENC}'):
    buff = "Content-Type: " + mime + "\n\n" + json.dumps(data)
    print(buff)
    return

  # テキストファイルを応答として返す。path はそのパス名。
  def sendText(self, path):
    buff = f"Content-Type: text/plain; charset={ENC}\n\n"
    with open(path, mode="rt", encoding="utf-8") as f:
      buff += f.read()
      print(buff)
    return

  # HTMLファイルを応答として返す。path はそのパス名。
  def sendHtml(self, path, cookie=True, embed=None):
    buff = ""
    if cookie:
      buff = self.makeCookie()
    buff += f"Content-Type: text/html; charset={ENC}\n\n"
    with open(path, mode="rt", encoding="utf-8") as f:
      buff += f.read()
      if isinstance(embed, dict):
        for k, v in embed.items():
          buff = buff.replace("{{" + k + "}}", v)
      print(buff)
    return

  # 画像ファイルを応答として返す。path はそのパス名。
  def sendImage(self, path):
    p = pathlib.Path(path)
    if p.suffix == '.jpg':
      img = b'jpeg'
    elif p.suffix == '.png':
      img = b'png'
    elif p.suffix == '.svg':
      img = 'svg+xml'
    else:
      img = b'gif'
    if p.suffix == '.svg':
      with open(path, mode="rt") as f:
        svg = f.read()
        buff = "Content-Type: image/" + img + "\n\n" + svg
        if isDebug():
          pprint(buff)
        else:
          print(buff)
    else:
      with open(path, mode="rb") as f:
        b = f.read()
        buff = b"Content-Type: image/" + img + b"\n\n" + b
        if isDebug():
          pprint(buff)
        else:
          sys.stdout.buffer.write(buff)
    return

  # 動画ファイルを応答として返す。path はそのパス名。
  def sendVideo(self, path):
    p = pathlib.Path(path)
    if p.suffix == '.mp4':
      video = "mp4"
    elif p.suffix == '.webm':
      video = "webm"
    else:
      video = "ogv"
    with open(path, mode="rb") as f:
      b = f.read()
      buff = b"Content-Type: video/" + video + b"\n\n" + b
      if isDebug():
        pprint(buff)
      else:
        sys.stdout.buffer.write(buff)
    return

  # 音声ファイルを応答として返す。path はそのパス名。
  def sendAudio(self, path):
    p = pathlib.Path(path)
    if p.suffix == '.mp3':
      audio = "mp3"
    elif p.suffix == '.m4a':
      audio = "aac"
    elif p.suffix == '.wav':
      audio = "wav"
    else:
      video = "ogg"
    with open(path, mode="rb") as f:
      b = f.read()
      buff = b"Content-Type: audio/" + audio + b"\n\n" + b
      if isDebug():
        pprint(buff)
      else:
        sys.stdout.buffer.write(buff)
    return

  # その他の形式のファイルを応答として返す。mime は ZIP="application/zip", PDF="application/pdf" など
  def sendFile(self, path, mime):
    bmm = bytes(mime, 'utf-8')
    with open(path, mode="rb") as f:
      b = f.read()
      buff = b"Content-Type: " + bmm + b"\n\n" + b
      if isDebug():
        pprint(buff)
      else:
        sys.stdout.buffer.write(buff)
    return

  # リダイレクト
  def redirect(self, url):
    print("Location: " + url + "\n")
    
  # HTTP ヘッダを出力 (headers は辞書で最後の項目は Content-Type であるものとする)
  def header(self, headers):
    s = ""
    for k, v in headers.items():
      s += k
      s += ": "
      s += v
      s += "\n"
    s += "\n"
    print(s)
