# CGI356Lib.py v1.3.0  2023-02-17
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
    self.RawData = ""                 #  受け取った生データ (文字列)
    self.RawBytes = ""                #  受け取った生データ (バイト列)
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
      bstr = bstr.replace("\\n", "\n").replace("\\r", "\r").replace("\\\\", "\\")
    else:
      pass
    return bstr

  # FormData 文字列から変数名をキーとする辞書を作成する。
  def parseFormData(self, s=""):
    state = 0
    name =""
    filename = ""
    octedstream = ""
    result = dict()
    # s がデフォルトの場合
    if s == "":
      s = self.RawData
    # b'...' を外す。
    s = self.btos(s)
    lines = s.split("\r\n")
    # 行ごと処理を行う。
    for line in lines:
      # state == 0 のとき、行に "Content-Disposition: form-data;" 見つかるまで読み飛ばす。
      if state == 0:
        if "Content-Disposition: form-data;" in line:
          m = line.split("name=\"")
          m2 = m[1].split("\"")
          name = m2[0]
          if "filename=" in line:
           # "filename=" が行に含まれるとき、filename を取得。
            m = line.split("filename=\"")
            m2 = m[1].split("\"")
            filename = m2[0]
            state = 1
          else:
            # "filename=" が含まれていないときは、input[type="file"] 以外
            state = 3
        else:
          continue  # それ以外の行は読み飛ばす。
      elif state == 1:
        # filename が空でないとき、Content-Type: application/octet-stream が含まれているか？
        if line == "":
              continue
        if filename == "":
          # filename == "" のときは、name に対する値を "" として、次の form-data まで読み飛ばす。
          result[name] = ""
          state = 0
        else:
          if 'Content-Type: application/octet-stream' in line:
            # アップロードされたファイル内容がある場合、次の行でその内容を取得する。
            state = 2
      elif state == 2:
        # ファイル内容(octed-stream)を取得する
        if line == "":
          continue
        octedstream = self.unescape(line)
        result[name] = [filename, octedstream]
        name = ""
        filename = ""
        state = 0  # ファイル処理終了
      elif state == 3:
        # input[type="file"] 以外の場合は空行を読み飛ばし、最初の非空行が値になる。
        if line == "":
          continue
        result[name] = line
        name = ""
        state = 0  # 一般コントロール処理終了
      else:
        pass
    return result

  # クライアントから受け取った生データ文字列をJSON形式とみなし変数名をキーとする辞書を作成する。
  def parseJSON(self, s=""):
    if s == "":
      s = self.RawData
    s = self.btos(s)
    result = json.loads(s)
    return result

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

  # エスケープ文字を元に戻す。
  def unescape(self, s):
    #s = s.fromPercent(s)
    result = s.replace("\\n", "\n") #.replace("\\t", "\t").replace("\\\\", "\\")
    return result
  
  # フォームデータを文字列にする。(デバッグ用)
  def formdataToString(self):
    s = ""
    for k, v in self.Form.items():
      if isinstance(v, dict):
        s += f"filename={v[0]}, octed-stream={v[1]};\n"
      else:
        s += f"{k}:{v[0]};\n"
    return s
  
  # 環境変数 QUERY_STRING から変数名をキーとする辞書を作成する。
  def _getQuery(self):
    result = dict()
    try:
      self.RawBytes = os.environ["QUERY_STRING"]
      if isDebug() and self.RawBytes != "":
        self.Method = "GET"
      self.RawData = self.fromPercent(self.RawBytes)
      params = urllib.parse.parse_qs(self.RawBytes)
      for key in params:
        result[key] = params[key][0]
    except Exception as e:
      pass
    return result

  # 標準入力から変数名をキーとする辞書を作成する。
  def _getForm(self):
    result = dict()
    bs = bytes()
    try:
      if isDebug():
        print("Enter form data > ")
        self.Method = 'POST'
        self.RawData = input()
      else:
        bs = sys.stdin.buffer.read()
      if self.RawData == "":
        self.RawData += bs.decode()
        self.RawBytes = bs
      s = self.RawData
      if s.startswith("-----"):
        # FormData
        result = self.parseFormData(s)
      else:
        # その他
        result = urllib.parse.parse_qs(s)
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
  def setCookie(self, cookies:dict):
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
  def sendString(self, s:str, mime=f'text/html; charset={ENC}', cookie=True, embed=None):
    if isinstance(embed, dict):
      for k, v in embed.items():
         s = s.replace("{{ " + k + " }}", v)
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
    buff += "Content-Type: " + mime + "\n\n" + s
    print(buff)
    return

  # 単純な文字列を返す。
  def sendSimple(self, s:str):
    print("Content-Type: text/plain\n\n" + s)
    return

  # pprint で単純な文字列を返す。(for Debug)
  def sendPPrint(self, s:str):
    print("Content-Type: text/plain\n")
    pprint(s)
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
    return

#  ユーティリティ
class CGIUtility:
  # HTML テーブルを作成する。
  @staticmethod
  def htmlTable(table="", tr="", th="", td=""):
    return

  # HTML リストを作成する。
  @staticmethod
  def htmlList(list="ul", ul="", li=""):
    return
  
  # SVG を作成する。(円 'circle' と正方形 'square' のみ)
  @staticmethod
  def svg(shape="circle", size=32, borderWidth=1, borderColor="black", bgcolor="white"):
    return

  

  
