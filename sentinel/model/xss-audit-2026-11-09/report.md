# XSS 資料涵蓋與特徵辨識診斷

日期：2026-11-09。只讀資料；沒有修改特徵、原文、分割、參數或部署模型。
本次為離線分類診斷，不發送 HTTP、不執行瀏覽器腳本；家族名稱是生成意圖，不代表漏洞成立。

| 集合 | XSS 筆數 | 不同 payload 原文 | 原文命中 XSS 專用模式 | 嵌入請求後新增專用訊號 | 原訊號消失 |
|---|---:|---:|---:|---:|---:|
| train | 84 | 10 | 84 | 76 | 8 |
| test | 28 | 3 | 0 | 0 | 0 |
| validation | 28 | 8 | 17 | 12 | 5 |

## 家族與位置差異

- train：家族 `{"xss.event": 57, "xss.url": 13, "xss.script": 14}`；位置 `{"header": 42, "body": 34, "query": 7, "path": 1}`。
- test：家族 `{"xss.js-string": 19, "xss.js-template": 9}`；位置 `{"header": 10, "query": 9, "body": 4, "path": 5}`。
- validation：家族 `{"external_unclassified": 28}`；位置 `{"path": 4, "header": 12, "query": 3, "body": 9}`。

訓練只有 script／event／URL 類；test 刻意保留 JS 字串／模板家族。這是未見家族、不同 API 與位置分布共同改變的測試，不能當成純粹隨機同分布測試。
validation 原資料未提供本地 family 欄，external_unclassified 是缺少這份分類資訊，不等於沒有家族或只有一種。
沒有 HTTP／儲存讀回／瀏覽器執行證據，因此本次不能確認反射型、儲存型或 DOM-XSS 的行為覆蓋；以上只量測請求可見的字串與來源家族。

## 具體辨識盲點

目前每段文字只有 16 項統計，XSS 專用模式只有 `<script`、`on…=`、`javascript:`；不計括號、反引號、美元符、花括號、`//`、`alert`、`void` 或屬性／JS 語境。
相同請求框架中，`${void(0)}` 與 `blue shirt` 的完整 278 維特徵相同：True。原文字串仍不同，這是特徵資訊不足，不是把資料正規化。
Query／Path 的必要傳輸編碼會把 `<`、`=`、`:` 等變成百分比字樣，原文 regex 不能直接看到；上表用正常配對作差，實際量測專用訊號是否消失。沒有解碼或改寫輸入。
正常 Query 被 event regex 命中的紀錄數：0；具體符合片段見 audit.json。這是特徵誤匹配，不必然等同模型誤判的因果證明。
跨集合或跨標籤相同向量群：3；其中混合標籤群：0。共用向量群不是原始請求重複筆數，見 feature-collisions.csv。
訓練 normal 對照中，命中目前三種 XSS 專用模式的筆數：0。若為 0，沒有檢查到可要求模型區分「看似 XSS 但合法」的這類正常對照；不能僅靠關鍵字共現宣稱語意辨識。

## 固定參數重現

使用目前程式相同的 150 棵樹、深度 3、seed=42；只 fit train，沒有用 test／validation 選參數。以下是本機重現，不冒充取得 Colab 逐筆預測檔。

```json
{
  "packages": {
    "numpy": "2.3.5",
    "scikit-learn": "1.7.2",
    "xgboost": "3.1.2"
  },
  "parameters_unchanged": true,
  "used_holdout_for_tuning": false,
  "results": {
    "train": {
      "confusion_matrix": [
        [
          84,
          0,
          0
        ],
        [
          1,
          83,
          0
        ],
        [
          2,
          0,
          82
        ]
      ],
      "accuracy": 0.9880952380952381,
      "matches_user_colab_matrix": null
    },
    "test": {
      "confusion_matrix": [
        [
          21,
          0,
          7
        ],
        [
          7,
          21,
          0
        ],
        [
          18,
          0,
          10
        ]
      ],
      "accuracy": 0.6190476190476191,
      "matches_user_colab_matrix": true
    },
    "validation": {
      "confusion_matrix": [
        [
          27,
          0,
          1
        ],
        [
          8,
          20,
          0
        ],
        [
          9,
          3,
          16
        ]
      ],
      "accuracy": 0.75,
      "matches_user_colab_matrix": true
    }
  },
  "top_features": [
    {
      "name": "headers.aggregate.sql_comment",
      "importance": 0.13735364377498627
    },
    {
      "name": "body.sql_comment",
      "importance": 0.1002340093255043
    },
    {
      "name": "headers.aggregate.lt",
      "importance": 0.07898655533790588
    },
    {
      "name": "headers.aggregate.xss_event",
      "importance": 0.07446246594190598
    },
    {
      "name": "headers.aggregate.equals",
      "importance": 0.06912460178136826
    },
    {
      "name": "body.equals",
      "importance": 0.0685291439294815
    },
    {
      "name": "body.xss_event",
      "importance": 0.06385579705238342
    },
    {
      "name": "headers.aggregate.sql_logic",
      "importance": 0.06004504859447479
    },
    {
      "name": "body.lt",
      "importance": 0.051949068903923035
    },
    {
      "name": "query.sql_logic",
      "importance": 0.045949406921863556
    },
    {
      "name": "body.sql_logic",
      "importance": 0.039849985390901566
    },
    {
      "name": "query.percent",
      "importance": 0.03849310427904129
    },
    {
      "name": "header.sw-language-id.length",
      "importance": 0.035137102007865906
    },
    {
      "name": "header.x-channel.length",
      "importance": 0.027850935235619545
    },
    {
      "name": "body.xss_url",
      "importance": 0.027550384402275085
    }
  ],
  "importance_by_block": {
    "method": 0.0,
    "content_type": 0.0,
    "query": 0.08709237724542618,
    "body": 0.3809593915939331,
    "path": 0.00925541017204523,
    "headers": 0.45970475673675537,
    "header": 0.0629880353808403
  },
  "xss_predictions_by_location": {
    "train": {
      "body": {
        "xss": 34
      },
      "header": {
        "xss": 42
      },
      "path": {
        "normal": 1
      },
      "query": {
        "xss": 6,
        "normal": 1
      }
    },
    "test": {
      "body": {
        "normal": 4
      },
      "header": {
        "normal": 9,
        "xss": 1
      },
      "path": {
        "normal": 5
      },
      "query": {
        "xss": 9
      }
    },
    "validation": {
      "body": {
        "sqli": 2,
        "xss": 7
      },
      "header": {
        "normal": 4,
        "xss": 7,
        "sqli": 1
      },
      "path": {
        "normal": 4
      },
      "query": {
        "xss": 2,
        "normal": 1
      }
    }
  }
}
```

### XSS 原文與本機預測分布

| 集合 | Payload 原文（JSON 字串） | 筆數 | 預測 normal | 預測 sqli | 預測 xss |
|---|---|---:|---:|---:|---:|
| train | `"' autofocus onfocus='void(0)' data-x='"` | 12 | 0 | 0 | 12 |
| train | `"x onmouseover=void(0)"` | 11 | 1 | 0 | 10 |
| train | `"&lt;svg onload=\"void(0)\"&gt;&lt;/svg&gt;"` | 15 | 0 | 0 | 15 |
| train | `"&lt;img src=\"data:image/png;base64,AA==\" onerror=\"void(0)\"&gt;"` | 6 | 0 | 0 | 6 |
| train | `"&lt;a href=\"javascript:void(0)\"&gt;View item&lt;/a&gt;"` | 6 | 0 | 0 | 6 |
| train | `"&lt;script&gt;void(0)&lt;/script&gt;"` | 6 | 0 | 0 | 6 |
| train | `"javascript:void(0)"` | 7 | 0 | 0 | 7 |
| train | `"\" autofocus onfocus=\"void(0)\" data-x=\""` | 4 | 0 | 0 | 4 |
| train | `"&lt;/script&gt;&lt;script&gt;void(0)&lt;/script&gt;"` | 8 | 1 | 0 | 7 |
| train | `"&lt;/style&gt;&lt;svg onload=\"void(0)\"&gt;&lt;/svg&gt;"` | 9 | 0 | 0 | 9 |
| test | `"\";void(0);//"` | 13 | 7 | 0 | 6 |
| test | `"';void(0);//"` | 6 | 5 | 0 | 1 |
| test | `"${void(0)}"` | 9 | 6 | 0 | 3 |
| validation | `"&gt;&lt;img id=xss src=x onerror=alert(xss);&gt;"` | 4 | 2 | 0 | 2 |
| validation | `"&gt;&lt;script&gt;alert(\"vlab\")&lt;/script&gt;"` | 5 | 5 | 0 | 0 |
| validation | `"&gt;\"&lt;input type=\"image\" src=\"javascript:document.cookie=true;\"&gt;"` | 4 | 0 | 0 | 4 |
| validation | `"&lt;xml id=xss&gt;&lt;x&gt;&lt;c&gt;&lt;![cdata[&lt;img id=xss src=\"javas]]&gt;&lt;![cdata[cript:alert('xss');\"&gt;]]&gt;&lt;/c&gt;&lt;/x&gt;&lt;xml&gt;&lt;span dataid=xss src=#i datafld=cdataformatas=html&gt;&lt;/span&gt;"` | 6 | 0 | 0 | 6 |
| validation | `"&lt;!--#exec cmd=\"/bin/echo '&lt;scr'\"--&gt;&lt;!--#exec cmd=\"/bin/echo 'ipt src=http://vulnerability-lab.com/crosssitescripting.js&gt;&lt;/script&gt;'\"--&gt;"` | 3 | 0 | 3 | 0 |
| validation | `"-1&lt;img src=\"blah\"onmouseover=\"document.cookie=true;\"&gt;"` | 3 | 0 | 0 | 3 |
| validation | `"open()&gt;"` | 2 | 2 | 0 | 0 |
| validation | `"&lt;link rel=\"stylesheet\" href=\"javascript:document.cookie=true;\"&gt;"` | 1 | 0 | 0 | 1 |

## 建議修正方向（本次未實作）

1. 保留這次基準與分割。將「已見家族的新請求」及「未見家族」設為不同實驗，不能為提高 test 分數把考題加回 train。
2. 在 train 內補齊有來源的 JS 字串／模板、不同編碼與位置、及合法程式碼文字／特殊符號的正常對照；各家族需多個獨立基底，不靠換尾數或同一 payload 套很多 API 湊數。
3. 不正規化原文；考慮新增原字元的字元 n-gram、JS 邊界符號與百分比編碼字樣特徵。詞彙與任何選擇只 fit train；關鍵字本身不證明攻擊，須搭配正常對照。
4. 採用受控的 train 內分組比較，再固定新版本。已看過的 test／Sylius 成績不能作反覆調參的依據；最終效果另保留新資料。
5. 附有 cmd／SSI、外部腳本 URL 或極短片段的外部樣本需查核語境與三分類標籤適用性；本次不執行、不自動改標籤。

完整逐筆結果：xss-samples.csv；來源 SHA、訊號統計與重現資訊：audit.json。
