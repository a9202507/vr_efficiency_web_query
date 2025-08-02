1. 系統名稱與簡述
# VR實測效率查詢系統
## 收集各式條件的實測效率，一般用戶可以透過前端上傳資料至後台資料庫，也可以透過條件找出特定資料，並且下載原始資料。管理者可以下載資料庫備份。

2. 系統需求：
    * 前端:
        * javascript
        * chart.js
    * 後端:
        * python
        * flask framework
        * SQLite
3. 資料庫設計 SQLite
    * 資料表:efficiency table
        |column_name| series number*|istep | vin | iin| vout | remote vout sense | iout | efficiency | efficiency_remote | user_id|
        |-|-|-|-|-|-|-|-|-|-|-|
        |data type|int|float|float|float|float|float|float|float|float|int|
    * 資料表:information table
        |column_name| user_ID*|user_name | pcb_name | powerstage_name| phase_count | frequency |inductor_value|tlvr| imax | upload_date | notice | 
        |-|-|-|-|-|-|-|-|-|-|-|-|
        |data type|int|str|str|str|int|int|int|int|int|TEXT|str|

4. 功能需求
    * 一般用戶:
        * 可透過前端介面上傳.csv到efficiency_table，在上傳的同時，需同步建立infomration_table
        * 可以多條件搜尋出各別efficiency_table的資料，例如找出所有powerstage_name= TDA22594A 以及6phase的efficinecy_table，並且同步畫面效率曲線在前端介面上。
        * 可下載指定的原始csv數據
    * 管理者:
        * 透過輸入密碼，取得管理者權限。
        * 管理者可以備份資料庫，備份時自動加上時間記號。
        * 管理者可以上傳資料庫的備份檔案，達到資料庫的還原功能
        * 管理者可以在前端介面增減efficiency_table的欄位
        * 管理者可以在前端介面增減information_table的欄位
5. 效能需求:
    * 可同時支援10用戶同時在線上
    * 上傳資料以.csv為主
6. 可用性需求：
    * 響應式網頁計設
    * 錯誤訊息友善提示
7. 上傳資料格式說明
        必要欄位：Istep, Vin, Iin, Vout, remote Vout sense, Iout, Efficiency, Efficiency_remote
        檔案編碼：UTF-8
        分隔符號：逗號