# WeatherCast
## OverView
Raspberry Pi上に構築したオリジナルシステム<br>
- 天気予報を取得し，SPI通信を通して専用の電子ペーパーに表示する
- cronで提示実行
- 天気予報は以下から取得
  - https://www.jma.go.jp/bosai/forecast/data/forecast/200000.json
  - https://tenki.jp/forecast/3/23/4810/20201/3hours.html
  - https://tenki.jp/forecast/3/23/4810/20201/

##Project Layout
-BackApp/
  - WeaterCast/
    - img/ : 天気コードに対応した画像
      - 100.png ~ 811.png
    - src/
      - Font.ttc
      - weather_code.json
      - weather.json
    - epd4in2.py
    - epdconfig.py
    - weather.py : 実行用ファイル
