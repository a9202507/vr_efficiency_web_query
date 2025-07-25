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