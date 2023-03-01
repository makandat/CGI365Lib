# CGI356Lib.py v1.5.4  2023-03-01
import os, sys, datetime, io
import subprocess
from subprocess import PIPE
import urllib.parse as urlp
import pathlib
import json
from pprint import pprint

# 文字コード
ENC = 'utf-8'
# デバッグ用ログファイル
LOG = ""

# デバッグ用 判別
def _isDebug():
  return len(sys.argv) > 1 and sys.argv[1] == "debug"

# デバッグ用 QUERY_STRING 設定
def setQueryString(qs):
  if _isDebug():
    os.environ["QUERY_STRING"] = qs

# デバッグ用 HTTP_COOKIE 設定
def setHttpCookie(cookie):
  if _isDebug():
    os.environ["HTTP_COOKIE"] = cookie

# デバッグ用 REQUEST_METHOD 設定
def setRequestMethod(method):
  if _isDebug():
    os.environ["REQUEST_METHOD"] = method

# デバッグ用ログ出力
def info(obj):
  if LOG == "":
    return
  now = datetime.datetime.now()
  strnow = now.isoformat()
  with open(LOG, mode="at") as f:
    f.write(strnow + " " + str(obj) + "\n")

# --------------------------------------------------------------------
#   Request class
# --------------------------------------------------------------------
class Request:
  def __init__(self):
    # Windows の場合はデフォルトの文字コードが Shift JIS なので、これがないと文字化けする。
    if os.name == 'nt':
      sys.stdin= io.TextIOWrapper(sys.stdin.buffer, encoding=ENC)
    self.RawData = b""                #  POST で受け取った生データ (バイト列または文字列)
    self.QueryString = ""             #  GET で受け取った環境変数 QUERY_STRING (文字列)
    self.Method = self._getMethod()   #  HTTP メソッド 'GET', 'POST'...
    self.Address = self._getAddress() #  アドレス 辞書 キーは 'Server', 'Client', 'Host'
    self.Query = self._getQuery()     #  GET のパラメータ 辞書
    self.Form = dict()                #  POST のパラメータ 辞書
    self.Cookie = self._getCookie()   #  クッキー 辞書
    return

  # CGI パラメータを得る。キーが存在しないときは空文字を返す。
  def getParam(self, key):
    if self.Method == "GET":
      if key in self.Query:
        return self.Query[key]
      else:
        return ""
    else:
      for block in self.Form:
        if key in block:
          return block[key]
        else:
          continue
      return ""

  # POST データを解析する。
  def parseFormBody(self):
    # コンソールアプリとしてデバッグするか？
    (debug, filePath) = self._getDebug()
    if debug == True:
      if filePath == '':
        print("Enter posted data > ", end='')
        s = input()
        buff = s.encode()
      else:
        with open(filePath, "rb") as f:
          buff = f.read()
    else:
      buff = sys.stdin.buffer.read()
    self.RawData = buff
    name = ""
    value = ""
    paramlist = list()
    if buff.startswith(b"-----"):
      # multipart/form-data を境界でブロックに分ける。
      blocks = self._parseMultiPart(buff)
      params = dict()
      state = 0
      # multipart/form-data のブロックごとに処理する。
      for block in blocks:
        # lines (行) と chunk (バイナリーデータ) に分ける。
        (lines, chunk) = block
        # 行ごとの処理
        for line in lines:
          # 空行は読み飛ばす。
          if line == b'':
            pass
          elif state == 0 and line.find(b"Content-Disposition: form-data;") == 0:
            # Content-Disposition 行の処理
            line = line[len(b"Content-Disposition: form-data;"):]
            p = line.find(b"name=\"")
            if p < 0:
              pass
            else:
              # name="..." から name 属性を取得する。
              line = line[p + 6:]
              p = line.find(b"\"")
              name = line[:p].decode()
              params["element-name"] = name
              line = line[p+2:]
              # ファイルアップロードの時は filename="..." があるのでファイル名を取得する。
              p = line.find(b"filename=\"")
              if p < 0:
                state = 1  # input[type="file"] でない場合
              else:
                # input[type="file"] の場合
                line = line[p+10:]
                p = line.find(b"\"")
                filename = line[:p].decode()
                params[f"filename-{name}"] = filename
                state = 2
          elif state == 1:
            # input[type="file"] でない場合 name に対する値を取得する。
            value = line.decode()
            params[name] = value
            state = 0  # 次の Content-Disposition へ
          elif state == 2 and line.find(b'Content-Type: ') == 0:
            # input[type="file"] の場合、Content-Type の内容を取得する。
            line = line[len(b'Content-Type: '):]
            params["type"] = line.decode()
            params[f"chunk-{name}"] = chunk  # アップロードされたファイル内容
            state = 0
          else:
            state = 0
        paramlist.append(params)
        params = dict()
      self.Form = paramlist
    else:
      # 普通のフォーム（マルチでない）
      params = urlp.parse_qs(buff.decode())
      items = dict()
      for k, v in params.items():
        items[k] = v[0]
      paramlist.append(items)
    self.Form = paramlist
    info("self.Form = " + str(self.Form))
    return

  # マルチパートのブロックを行に分割する。
  def _makeLines(self, block:bytes):
    lines = list()
    chunk = b''
    while True:
      p = block.find(b"\r\n")
      if p < 0:
        break
      line = block[0:p]
      lines.append(line)
      if b"Content-Type:" in line:
        chunk = block[p+4:-2]
        break
      block = block[p+2:]
    return (lines, chunk)

  # マルチパートフォームデータを解析する。
  def _parseMultiPart(self, buff):
    # マルチパートの境界を得る。
    WEBKIT = b"------WebKitFormBoundary"
    MOZILLA = b"------------------------"
    p = buff.find(WEBKIT)
    if p < 0:
      p = buff.find(MOZILLA)
      if p < 0:
        pass # エラー
    else:
      pass
    # ブロックのリスト
    blocks = list()
    # 境界線の全体を得る。
    q = buff.find(b"\x0d\x0a")
    boundary = buff[0:q]
    lenb = len(boundary)
    p = lenb + 2
    buff = buff[p:]
    # 境界線で生データ全体を分割する。
    while True:
      # 次の境界線を探す。
      p = buff.find(boundary)
      if p < 0:
        break
      (lines, chunk) = self._makeLines(buff[:p])
      blocks.append((lines, chunk))
      p += lenb + 2
      buff = buff[p:]
    return blocks

  # クライアントから受け取った生データ文字列をJSON とみなし辞書を作成する。
  def parseJSON(self):
    # コンソールアプリとしてデバッグするか？
    (debug, filePath) = self._getDebug()
    if debug == True:
      if filePath == '':
        print("Enter posted data > ", end='')
        s = input()
      else:
        with open(filePath, "r") as f:
          s = f.read()
    else:
      # ノーマル動作
      s = sys.stdin.read()
    info("s=" + s)
    self.RawData = s
    result = json.loads(s)
    return result
  
  # クライアントから受け取った生データを BLOB とみなし、self.RawData に格納する。
  def getRawData(self):
    # コンソールアプリとしてデバッグするか？
    (debug, filePath) = self._getDebug()
    if debug == True:
      if filePath == '':
        print("Enter posted data > ", end='')
        s = input()
        self.RawData = s.encode()
      else:
        with open(filePath, "rb") as f:
          self.RawData = f.read()
    else:
      # ノーマル動作
      self.RawData = sys.stdin.buffer.read()
    return self.RawData
  
  # クライアントから受け取った生データを BLOB とみなし、self.RawData に格納する。
  # さらに path が "" でないならファイルのパスとみなしファイル保存する。
  def saveAsBLOB(self, path):
    # コンソールアプリとしてデバッグするか？
    (debug, filePath) = self._getDebug()
    if debug == True:
      if filePath == '':
        print("Enter posted data > ", end='')
        s = input()
        self.RawData = s.encode()
      else:
        with open(filePath, "rb") as f:
          self.RawData = f.read()
    else:
      # ノーマル動作
      self.RawData = sys.stdin.buffer.read()
    with open(path, "wb") as f:
      f.write(self.RawData)
    return

  # クライアントから受け取った生データを UTF-8 文字列とみなし、self.RawData に格納する。
  def getRawString(self):
    # コンソールアプリとしてデバッグするか？
    (debug, filePath) = self._getDebug()
    if debug == True:
      if filePath == '':
        print("Enter posted data > ", end='')
        s = input()
        self.RawData = s
      else:
        with open(filePath, "r") as f:
          self.RawData = f.read()
    else:
      # ノーマル動作
      self.RawData = sys.stdin.read()
    return self.RawData
  
  # クライアントから受け取った生データを UTF-8 文字列とみなし、self.RawData に格納する。
  # さらに path が "" でないならファイルのパスとみなしファイル保存する。
  def saveAsRawString(self, path):
    # コンソールアプリとしてデバッグするか？
    (debug, filePath) = self._getDebug()
    if debug == True:
      if filePath == '':
        print("Enter posted data > ", end='')
        s = input()
        self.RawData = s
      else:
        with open(filePath, "r") as f:
          self.RawData = f.read()
    else:
      self.RawData = sys.stdin.read()
    with open(path, "w") as f:
      f.write(self.RawData)
    return

  # フォームデータを文字列にする。(デバッグ用)
  def formdataToString(self):
    s = ""
    for block in self.Form:
      for k, v in block.items():
        s += f"{k}:{v}, "
    return s
  
  # 環境変数 QUERY_STRING から変数名をキーとする辞書を作成する。
  def _getQuery(self) -> dict:
    if _isDebug() == False:
      if self.Method != "GET":
        return
    result = dict()
    try:
      self.QueryString = os.environ["QUERY_STRING"]
      params = urlp.parse_qs(self.QueryString)
      for key in params:
        result[key] = params[key][0]
    except Exception as e:
      result["error"] = str(e)
    return result

  # 環境変数 REQUEST_METHOD から HTTP メソッド名を返す。
  def _getMethod(self) -> str:
    method = "GET"
    try:
      if _isDebug() == False:
        method = os.environ["REQUEST_METHOD"]
      else:
        if self.Method != "":
          method = self.Method
    except:
      method = ""
    return method

  # 環境変数 HTTP_COOKIE からクッキー名をキーとする辞書を返す。
  def _getCookie(self) -> dict:
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
  def _getAddress(self) -> dict:
    address = dict()
    try:
      address['Server'] = os.environ["SERVER_ADDR"] + ":" + os.environ["SERVER_PORT"]
      address['Client'] = os.environ["REMOTE_ADDR"] + ":" + os.environ["REMOTE_PORT"]
      address['Host'] = os.environ["HTTP_HOST"]
    except:
      pass
    return address

  # Request.RawData を保存する。(self.RawData が取得済みであること)
  def saveRawData(self, savePath):
    with open(savePath, "wb") as f:
      f.write(self.RawData)
    return
  
  # filename と chunk を得る。
  def _getChunk(self, name):
    fstr = b"form-data; name=\"" + name.encode() + b"\""
    data = self.RawData
    p = data.find(fstr)
    if p >= 0:
        data1 = data[p:]
        p = data1.find(b"filename=\"")
        data1 = data1[p+10:]
        q = data1.find(b"\"")
        filename = data1[0:q].decode()
        data1 = data1[q+1:]
        p = data1.find(b"Content-Type:")
        data1 = data1[p+13:]
        p = data1.find(b"\r\n\r\n")
        data1 = data1[p+4:]
        q = data1.find(b"-----")
        chunk = data1[0:q-2]
        return (filename, chunk)
    else:
        return (b"", b"")
  
  # request.RawData の中の指定した name の生データ (octed-stream) を saveDir/filename でファイル保存する。
  def saveChunk(self, name, saveDir):
    (filename, chunk) = self._getChunk(name)
    if filename == "":
      return False
    path = saveDir + "/" + filename
    with open(path, "wb") as f:
      f.write(chunk)
    return True

  # デバッグ用のファイルを得る。
  def _getDebug(self):
    if len(sys.argv) > 1:
      if sys.argv[1] == 'debug':
        return (True, '')
      elif os.path.exists(sys.argv[1]):
        return (True, sys.argv[1])
      else:
        return (False, '')
    else:
      return (False, '')

# --------------------------------------------------------------------
# Response class
# --------------------------------------------------------------------
class Response:
  def __init__(self):
    # Windows の場合はデフォルトの文字コードが Shift JIS なので、これがないと文字化けする。
    if os.name == 'nt':
      sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=ENC)
    self.Cookie = list()
    self.Headers = list()
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
  def sendString(self, s:str, mime="", cookie=True, headers=True, embed=None):
    if isinstance(embed, dict):
      for k, v in embed.items():
         s = s.replace("{{ " + k + " }}", v)
    buff = ""
    if cookie:
      buff = self.makeCookie()
    if headers and len(self.Headers) > 0:
      for h in self.Headers:
        buff += h + "\n"
    if mime == "":
      buff += "Content-Type: text/html\n\n" + s
    else:
      buff += "Content-Type: " + mime + "\n\n" + s
    print(buff)
    return

  # 単純な文字列を返す。
  def sendSimple(self, s:str, charset=""):
    if charset == "":
      print("Content-Type: text/plain\n\n" + s)
    else:
      print(f"Content-Type: text/plain; charset={charset}\n\n" + s)
    return

  # pprint でオブジェクトを文字列にして返す。(for Debug)
  def sendPPrint(self, obj, charset=""):
    if charset == "":
      print("Content-Type: text/plain\n")
    else:
      print(f"Content-Type: text/plain; charset={charset}\n")
    pprint(obj)
    return

  # バイナリーデータを返す。
  def sendBinData(self, data):
    sys.stdout.buffer.write(b"Content-Type: application/octet-stream\n\n" + data)
    return

  # データを JSON に変換し応答として返す。
  def sendJSON(self, data, charset=""):
    if charset == "":
      print("Content-Type: application/json\n")
    else:
      print(f"Content-Type: application/json; charset={charset}\n")
    buff = json.dumps(data)
    print(buff)
    return

  # テキストファイルを応答として返す。path はそのパス名。
  def sendText(self, path, charset=""):
    if charset == "":
      buff = f"Content-Type: text/plain\n\n"
    else:
      buff = f"Content-Type: text/plain; charset={charset}\n\n"
    with open(path, mode="rt", encoding="utf-8") as f:
      buff += f.read()
      print(buff)
    return

  # HTMLファイルを応答として返す。path はそのパス名。
  def sendHtml(self, path, charset="", cookie=True, embed=None):
    buff = ""
    if cookie:
      buff = self.makeCookie()
    if charset == "":
      buff += f"Content-Type: text/html\n\n"
    else:
      buff += f"Content-Type: text/html; charset={charset}\n\n"
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
        if _isDebug():
          pprint(buff)
        else:
          print(buff)
    else:
      with open(path, mode="rb") as f:
        b = f.read()
        buff = b"Content-Type: image/" + img + b"\n\n" + b
        if _isDebug():
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
      if _isDebug():
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
      if _isDebug():
        pprint(buff)
      else:
        sys.stdout.buffer.write(buff)
    return

  # その他の形式のファイルを応答として返す。mime は ZIP="application/zip", PDF="application/pdf" など
  def sendFile(self, path, mime, filename=""):
    bmm = bytes(mime, 'utf-8')
    buff = ""
    with open(path, mode="rb") as f:
      b = f.read()
      if filename != "":
        buff += f"Content-Disposition: attachment; filename={filename}\n"
      buff += b"Content-Type: " + bmm + b"\n\n" + b
      if _isDebug():
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
class Utility:
  # HTML テーブルを作成する。
  @staticmethod
  def htmlTable(data, header=None, table="", tr="", th="", td=""):
    html = ""
    if table == "":
      html += "<table>\n"
    else:
      html += f"<table class=\"{table}\">\n"
    if isinstance(header, list):
      html += "<tr>\n"
      for col in header:
        if th == "":
          html += f"<th>{col}</th>"
        else:
          html += f"<th class=\"{th}\">{col}</th>"
      html += "</tr>\n"
    for row in data:
      if tr == "":
        html += "<tr>"
      else:
        html += f"<tr class=\"{tr}\">\n"
      for col in row:
        if td == "":
          html += f"<td>{col}</td>"
        else:
          html += f"<td class=\"{td}\">{col}</td>"
      html += "</tr>\n"
    html += "</table>\n"
    return html

  # HTML リストを作成する。
  @staticmethod
  def htmlList(data, list="ul", ul="", li=""):
    html = ""
    if ul == "":
      html += f"<{list}>"
    else:
      html += f"<{list} class=\"{ul}\">"
    for item in data:
      if li == "":
        html += "<li>"
      else:
        html += f"<li class={li}>"
      html += f"{item}</li>\n"
    html += f"</{list}>\n"
    return html
  
  # SVG を作成する。(円 'circle' と正方形 'square' のみ)
  @staticmethod
  def svg(shape, size=32, borderWidth=1, borderColor="black", bgColor="white"):
    svg = "<svg width=\"{0}\" height=\"{0}\">\n".format(size)
    if shape == "circle":
      x = size / 2
      y = size / 2
      r = size / 2
      svg += f"<circle cx=\"{x}\" cy=\"{y}\" r=\"{r}\" stroke-width=\"{borderWidth}\" stroke=\"{borderColor}\" fill=\"{bgColor}\" />\n"
    elif shape == "square":
      svg += f"<rect x=\"0\" y=\"0\" width=\"{size}\" height=\"{size}\" stroke-width=\"{borderWidth}\" stroke=\"{borderColor}\" fill=\"{bgColor}\" />\n"
    else:
      svg += "<text x=\"0\" y=\"0\" stroke=\"red\" font-size=\"30\">Error: Bad shape</svg>"
    svg += "</svg>\n"
    return svg

  # プロセスを起動する。
  @staticmethod
  def startProcess(cmd, *args):
    for a in args:
      cmd += " " + a
    proc = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
    result = proc.stdout
    return result
