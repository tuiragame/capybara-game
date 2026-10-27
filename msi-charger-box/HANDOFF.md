# 交接紀錄：MSI 400W 充電器散熱盒

給新會話的 Claude：請先讀這份，再讀 `README.md` 和 `msi_charger_box.scad`。
**使用者偏好：中文一律用繁體中文回覆。**

## 目標
使用者有一顆 MSI 400W 充電器（A23-400P1A，20V/20A，配 MSI Raider A18 HX A9W），很燙，
放地板會把地板烤熱。需要一個 3D 列印的通風盒：離地、四面透氣、不悶熱。

## 目前成果（分支 `claude/msi-charger-cooling-box-wnvhqz`，目錄 `msi-charger-box/`）
- `msi_charger_box.scad`：參數式 OpenSCAD 設計
- `plate.3mf`（盒身 + 蓋子同板）、`box.3mf`、`lid.3mf`，另有同名 `.stl`
- `preview_*.png`：預覽圖
- 設計：4 隻 14mm 腳、底板整面開孔、6 個墊塊抬高變壓器、兩長邊直槽、兩端 U 型電線缺口、
  蓋子有長條散熱孔（可選）。外形約 201 × 101 × 68mm，蓋子 7mm 高。
- 使用者的印表機：**Bambu Lab P1S**（256×256×256mm），plate.3mf 約 201×217×68 放得下，不需支撐。
- 建議材料 PETG 或 ABS/ASA，不要 PLA（變壓器表面可能 50–60°C）。

## 尚未解決：變壓器尺寸未確認
- 目前使用 `ad_L=189, ad_W=89, ad_H=34`（實測值 188.09 × 88.17 × 33.2 進位加公差）。
- 來源：ChargerLab 拆解報告
  https://www.chargerlab.com/teardown-of-the-msi-400w-adapter-a23-400p1a/
  但雲端環境網路政策擋住此網站（403 / ENOTFOUND），**無法開啟原文**，
  只在一次搜尋摘要中看過這組數字，之後的搜尋無法再現。
- 零售商 sparepartworld 標示 188×88×188mm，第三個數字明顯有誤。
- 長寬（188×88）有兩個來源吻合，較可信；**厚度 33.2mm 未確認**。
- A400A001P 型號沒有獨立的實測資料。

## 下一步
1. 取得確切尺寸：使用者自己量（游標卡尺，不含電線護套）、或從上面網址取得，貼給 Claude。
   （使用者問過怎麼讓雲端會話用他電腦的網路：需改用 Claude 桌面版，
   或在電腦上執行 `claude remote-control`；或到環境設定把網站加入 Allowed domains。）
2. 若與 189×89×34 有出入，修改 `.scad` 開頭三個數字，重新匯出：
   ```
   openscad -o box.3mf   -D 'part="box"'  msi_charger_box.scad
   openscad -o lid.3mf   -D 'part="lid"'  msi_charger_box.scad
   openscad -o plate.3mf -D 'part="both"' msi_charger_box.scad
   ```
   （STL 同理改副檔名。需要 `apt-get update && apt-get install -y openscad`；
   預覽圖用 `xvfb-run -a openscad -o x.png ...`。）
3. 提交並推送到同一分支，再把 3MF 傳給使用者。不要建立 PR，除非使用者要求。

## 已知細節
- 之前的錯誤：底板開孔曾沒置中，已修正。蓋子列印方向已修正為平面朝下。
- 可選：做一個只有一端的 5cm 試裝片，先確認變壓器放得進去。
