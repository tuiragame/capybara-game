// MSI A23-400P1A (400W, 20V/20A) 充電器散熱架 / vented stand-box
// 參數式設計：先量你自己那顆的實際尺寸，改下面三個數字就好。
// Render: openscad -o box.3mf -D 'part="box"' msi_charger_box.scad
//         openscad -o lid.3mf -D 'part="lid"' msi_charger_box.scad

part = "both";            // "box" | "lid" | "both" | "assembly"

// ---- 變壓器尺寸 (mm) ----
// 來源：ChargerLab 對 A23-400P1A 的拆解實測 188.09 x 88.17 x 33.20，
// 這裡各進位並留一點公差。你手上那顆若不同，量過後改這三個數字即可。
ad_L = 189;               // 長 (不含兩端電線護套)
ad_W = 89;                // 寬
ad_H = 34;                // 厚

// ---- 設計參數 ----
clr      = 3;             // 四周間隙 (每邊)
wall     = 3;             // 牆厚
base_t   = 4;             // 底板厚
foot_h   = 14;            // 腳高 = 底板離地面的空氣層
pad_h    = 6;             // 墊塊高度：把變壓器從底板抬起，讓底下也有風
top_gap  = 10;            // 變壓器頂面到蓋子的空間
cable_w  = 30;            // 電線缺口寬度 (護套約 12~15mm，留餘裕)
slot_w   = 10;            // 側牆直槽寬
rib      = 6;             // 槽與槽之間的肋條寬

// ---- 推導尺寸 ----
in_L  = ad_L + 2*clr;
in_W  = ad_W + 2*clr;
in_H  = pad_h + ad_H + top_gap;      // 內部高度 (不含底板)
out_L = in_L + 2*wall;
out_W = in_W + 2*wall;
wall_H = base_t + in_H;              // 底板頂面起算到牆頂

$fn = 40;

module rrect(x, y, h, r=3) {
    linear_extrude(h) offset(r) square([x-2*r, y-2*r], center=true);
}

// 沿長度方向排一排槽 (中心對稱)
module slot_row(n, pitch, w, h, depth) {
    for (i = [0:n-1])
        translate([(i-(n-1)/2)*pitch, 0, 0]) cube([w, depth, h], center=true);
}

module foot_set() {
    fx = out_L/2 - 14;
    fy = out_W/2 - 14;
    for (sx=[-1,1], sy=[-1,1])
        translate([sx*fx, sy*fy, 0]) rrect(24, 24, foot_h, 4);
}

module box() {
    translate([0, 0, foot_h]) {
        difference() {
            union() {
                // 外殼
                rrect(out_L, out_W, wall_H, 5);
            }
            // 內腔
            translate([0, 0, base_t]) rrect(in_L, in_W, in_H+1, 2);

            // ---- 底板開孔 (熱空氣往上、冷空氣從底下補進來) ----
            sl = 40; sg = 8;   // 孔長 / 孔間肋
            nx = floor((in_L-20)/(sl+sg));
            ny = floor((in_W-10)/(slot_w+rib));
            for (ix=[0:nx-1], iy=[0:ny-1])
                translate([(ix-(nx-1)/2)*(sl+sg), (iy-(ny-1)/2)*(slot_w+rib), -0.1])
                    cube([sl, slot_w, base_t+0.2], center=false);

            // ---- 兩長邊側牆直槽 ----
            ns = floor((in_L-30)/(slot_w+rib));
            sz0 = base_t + 3;
            sz1 = wall_H - 7;               // 牆頂留一圈肋條增加剛性
            for (sy=[-1,1])
                translate([0, sy*(out_W/2 - wall/2), (sz0+sz1)/2])
                    slot_row(ns, slot_w+rib, slot_w, sz1-sz0, wall+2);

            // ---- 兩短邊：電線 U 型缺口 (從上面放進去) ----
            for (sx=[-1,1])
                translate([sx*(out_L/2 - wall/2), 0, 0]) {
                    // 缺口
                    translate([0, 0, base_t+pad_h+ad_H/2 + (wall_H)/2 - 1])
                        cube([wall+2, cable_w, wall_H - (base_t+pad_h+ad_H/2) + 2], center=true);
                    // 缺口底部圓角
                    translate([0, 0, base_t+pad_h+ad_H/2])
                        rotate([0,90,0]) cylinder(d=cable_w, h=wall+2, center=true);
                    // 兩側小直槽
                    for (sy=[-1,1])
                        translate([0, sy*(cable_w/2 + 14), (base_t+3 + wall_H-7)/2])
                            cube([wall+2, slot_w, wall_H-7-(base_t+3)], center=true);
                }
        }
        // ---- 墊塊：6 顆，四面八方都能過風 ----
        for (px=[-1,0,1], py=[-1,1])
            translate([px*(in_L/2-30)*(px==0?0:1), py*(in_W/4), base_t])
                rrect(16, 16, pad_h, 2);
        // ---- 防止變壓器橫向滑動的小擋塊 ----
        for (sx=[-1,1], sy=[-1,1])
            translate([sx*(in_L/2 - 1.5), sy*(in_W/2 - 12), base_t])
                cube([3, 16, pad_h+12], center=true);
    }
    foot_set();
}

// 列印方向：翻過來，平面朝下、凸緣朝上
module print_lid() { rotate([180,0,0]) translate([0,0,-4]) lid(); }

module lid() {
    lt = 4;
    difference() {
        union() {
            rrect(out_L, out_W, lt, 5);
            // 定位凸緣：卡進牆內側，不會滑掉
            translate([0, 0, -3]) difference() {
                rrect(in_L-1, in_W-1, 3, 2);
                translate([0,0,-0.1]) rrect(in_L-1-8, in_W-1-8, 3.2, 2);
            }
        }
        // 長條散熱孔 (沿長度方向)
        ny = floor((in_W-16)/(slot_w+rib));
        for (iy=[0:ny-1])
            translate([0, (iy-(ny-1)/2)*(slot_w+rib), lt/2])
                cube([in_L-40, slot_w, lt+1], center=true);
    }
}

if (part == "box")  box();
if (part == "lid")  print_lid();
if (part == "both") { box(); translate([0, out_W+15, 0]) print_lid(); }
if (part == "assembly") {
    box();
    translate([0, 0, foot_h+wall_H+0.01]) lid();
    // 示意變壓器
    %translate([0,0,foot_h+base_t+pad_h+ad_H/2]) cube([ad_L, ad_W, ad_H], center=true);
}
