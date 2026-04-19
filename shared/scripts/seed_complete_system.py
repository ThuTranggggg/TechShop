#!/usr/bin/env python3
"""
Master seed orchestration script for TechShop microservices.

This version is aligned with the current codebase and routes:
- Uses public/auth APIs where available.
- Uses Docker manage.py shell fallback for services that do not expose write APIs
  (notably product_service/order_service in this repository state).
- Keeps seeding idempotent (safe to run multiple times).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]

SERVICE_URLS = {
    "user": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
    "product": os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8002"),
    "cart": os.getenv("CART_SERVICE_URL", "http://localhost:8003"),
    "order": os.getenv("ORDER_SERVICE_URL", "http://localhost:8004"),
    "payment": os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8005"),
    "shipping": os.getenv("SHIPPING_SERVICE_URL", "http://localhost:8006"),
    "inventory": os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8007"),
    "ai": os.getenv("AI_SERVICE_URL", "http://localhost:8008"),
}

INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "internal-secret-key")

DEMO_USERS = [
    {"email": "admin@example.com", "full_name": "Admin User", "phone_number": "+84912345670"},
    {"email": "staff@example.com", "full_name": "Staff User", "phone_number": "+84912345671"},
    {"email": "john@example.com", "full_name": "John Doe", "phone_number": "+84912345680"},
    {"email": "jane@example.com", "full_name": "Jane Doe", "phone_number": "+84912345681"},
]

DEMO_PASSWORD = "Demo@123456"

DEMO_CATEGORY_TREE = [
    {"slug": "dien-tu", "name": "Dien tu", "parent": None, "description": "Nhom product gom thiet bi dien tu va phu kien cong nghe phuc vu hoc tap, lien lac va giai tri hang ngay.", "image_url": "https://picsum.photos/seed/dien-tu/1200/800", "sort_order": 1},
    {"slug": "dien-thoai-va-may-tinh-bang", "name": "Dien thoai va may tinh bang", "parent": "dien-tu", "description": "Danh muc smartphone va tablet cho hoc tap, giai tri, lam viec di dong va lien lac moi ngay.", "image_url": "https://picsum.photos/seed/dien-thoai-va-may-tinh-bang/1200/800", "sort_order": 2},
    {"slug": "phu-kien-cong-nghe", "name": "Phu kien cong nghe", "parent": "dien-tu", "description": "Danh muc pin du phong, tai nghe, sac nhanh va cac phu kien ho tro he sinh thai thiet bi so.", "image_url": "https://picsum.photos/seed/phu-kien-cong-nghe/1200/800", "sort_order": 3},
    {"slug": "thoi-trang", "name": "Thoi trang", "parent": None, "description": "Nhom product thoi trang cho nhu cau mac dep, di lam, di hoc va su dung hang ngay.", "image_url": "https://picsum.photos/seed/thoi-trang/1200/800", "sort_order": 4},
    {"slug": "thoi-trang-nam", "name": "Thoi trang nam", "parent": "thoi-trang", "description": "Danh muc ao, quan va set do co ban cho phong cach nam tinh, de mac va de phoi.", "image_url": "https://picsum.photos/seed/thoi-trang-nam/1200/800", "sort_order": 5},
    {"slug": "thoi-trang-nu", "name": "Thoi trang nu", "parent": "thoi-trang", "description": "Danh muc dam, ao khoac va trang phuc nu cho cong so, dao pho va su kien nho.", "image_url": "https://picsum.photos/seed/thoi-trang-nu/1200/800", "sort_order": 6},
    {"slug": "my-pham", "name": "My pham", "parent": None, "description": "Nhom product lam dep gom cham soc da va trang diem co ban cho nhu cau ca nhan.", "image_url": "https://picsum.photos/seed/my-pham/1200/800", "sort_order": 7},
    {"slug": "cham-soc-da", "name": "Cham soc da", "parent": "my-pham", "description": "Danh muc serum, kem duong va san pham duong am phu hop routine sang toi.", "image_url": "https://picsum.photos/seed/cham-soc-da/1200/800", "sort_order": 8},
    {"slug": "trang-diem", "name": "Trang diem", "parent": "my-pham", "description": "Danh muc cushion, son va san pham makeup phu hop phong cach tu nhien den noi bat.", "image_url": "https://picsum.photos/seed/trang-diem/1200/800", "sort_order": 9},
    {"slug": "nha-cua-doi-song", "name": "Nha cua doi song", "parent": None, "description": "Nhom product gia dung va trang tri cho phong bep, phong ngu va khong gian song.", "image_url": "https://picsum.photos/seed/nha-cua-doi-song/1200/800", "sort_order": 10},
    {"slug": "do-bep", "name": "Do bep", "parent": "nha-cua-doi-song", "description": "Danh muc noi chien, chao, dung cu bep giup nau an nhanh va gon gang hon.", "image_url": "https://picsum.photos/seed/do-bep/1200/800", "sort_order": 11},
    {"slug": "trang-tri-nha-cua", "name": "Trang tri nha cua", "parent": "nha-cua-doi-song", "description": "Danh muc den ngu, ke trang tri va vat dung giup khong gian song am cung hon.", "image_url": "https://picsum.photos/seed/trang-tri-nha-cua/1200/800", "sort_order": 12},
    {"slug": "me-va-be", "name": "Me va be", "parent": None, "description": "Nhom product phuc vu cham soc tre nho va do dung thiet yeu cho me va be.", "image_url": "https://picsum.photos/seed/me-va-be/1200/800", "sort_order": 13},
    {"slug": "do-so-sinh", "name": "Do so sinh", "parent": "me-va-be", "description": "Danh muc quan ao so sinh, khan sua va vat dung mem mai cho giai doan dau doi.", "image_url": "https://picsum.photos/seed/do-so-sinh/1200/800", "sort_order": 14},
    {"slug": "sua-va-bim", "name": "Sua va bim", "parent": "me-va-be", "description": "Danh muc sua cong thuc, bim ta va cac san pham tieu hao cho be hang ngay.", "image_url": "https://picsum.photos/seed/sua-va-bim/1200/800", "sort_order": 15},
    {"slug": "the-thao-da-ngoai", "name": "The thao da ngoai", "parent": None, "description": "Nhom product tap luyen va da ngoai cho nhu cau van dong, trekking va cam trai.", "image_url": "https://picsum.photos/seed/the-thao-da-ngoai/1200/800", "sort_order": 16},
    {"slug": "do-tap-luyen", "name": "Do tap luyen", "parent": "the-thao-da-ngoai", "description": "Danh muc tham yoga, ta tay va dung cu giup tap luyen tai nha linh hoat.", "image_url": "https://picsum.photos/seed/do-tap-luyen/1200/800", "sort_order": 17},
    {"slug": "da-ngoai-cam-trai", "name": "Da ngoai cam trai", "parent": "the-thao-da-ngoai", "description": "Danh muc leu, binh giu nhiet va do da ngoai cho nhung chuyen di cuoi tuan.", "image_url": "https://picsum.photos/seed/da-ngoai-cam-trai/1200/800", "sort_order": 18},
    {"slug": "sach-van-phong-pham", "name": "Sach van phong pham", "parent": None, "description": "Nhom product sach ky nang va van phong pham cho hoc tap, lam viec va ghi chu.", "image_url": "https://picsum.photos/seed/sach-van-phong-pham/1200/800", "sort_order": 19},
    {"slug": "sach-ky-nang", "name": "Sach ky nang", "parent": "sach-van-phong-pham", "description": "Danh muc sach ky nang mem, tai chinh va phat trien ban than cho nguoi hoc va di lam.", "image_url": "https://picsum.photos/seed/sach-ky-nang/1200/800", "sort_order": 20},
    {"slug": "van-phong-pham", "name": "Van phong pham", "parent": "sach-van-phong-pham", "description": "Danh muc so tay, but viet va do dung ban hoc de to chuc cong viec hieu qua.", "image_url": "https://picsum.photos/seed/van-phong-pham/1200/800", "sort_order": 21},
    {"slug": "thuc-pham-do-uong", "name": "Thuc pham do uong", "parent": None, "description": "Nhom product do an vat, ca phe va thuc uong dong goi cho nhu cau tich tru tai nha va van phong.", "image_url": "https://picsum.photos/seed/thuc-pham-do-uong/1200/800", "sort_order": 22},
    {"slug": "do-an-vat", "name": "Do an vat", "parent": "thuc-pham-do-uong", "description": "Danh muc snack lanh manh, hat dinh duong va mon an nhe de su dung moi ngay.", "image_url": "https://picsum.photos/seed/do-an-vat/1200/800", "sort_order": 23},
    {"slug": "do-uong-pha-san", "name": "Do uong pha san", "parent": "thuc-pham-do-uong", "description": "Danh muc ca phe, tra va thuc uong pha nhanh phu hop tai nha va noi lam viec.", "image_url": "https://picsum.photos/seed/do-uong-pha-san/1200/800", "sort_order": 24},
    {"slug": "suc-khoe-ca-nhan", "name": "Suc khoe ca nhan", "parent": None, "description": "Nhom product cham soc suc khoe, vitamin bo sung va vat dung ca nhan hang ngay.", "image_url": "https://picsum.photos/seed/suc-khoe-ca-nhan/1200/800", "sort_order": 25},
    {"slug": "vitamin-bo-sung", "name": "Vitamin bo sung", "parent": "suc-khoe-ca-nhan", "description": "Danh muc vitamin, collagen va san pham bo sung cho muc tieu suc khoe va sac dep.", "image_url": "https://picsum.photos/seed/vitamin-bo-sung/1200/800", "sort_order": 26},
    {"slug": "cham-soc-ca-nhan", "name": "Cham soc ca nhan", "parent": "suc-khoe-ca-nhan", "description": "Danh muc ban chai dien, may cham soc va san pham ho tro ve sinh ca nhan.", "image_url": "https://picsum.photos/seed/cham-soc-ca-nhan/1200/800", "sort_order": 27},
    {"slug": "do-choi-giai-tri", "name": "Do choi giai tri", "parent": None, "description": "Nhom product do choi giao duc, boardgame va mo hinh cho gia dinh va tre em.", "image_url": "https://picsum.photos/seed/do-choi-giai-tri/1200/800", "sort_order": 28},
    {"slug": "do-choi-giao-duc", "name": "Do choi giao duc", "parent": "do-choi-giai-tri", "description": "Danh muc do choi hoc tap giup tre phat trien tu duy, mau sac va ky nang nen tang.", "image_url": "https://picsum.photos/seed/do-choi-giao-duc/1200/800", "sort_order": 29},
    {"slug": "boardgame-mo-hinh", "name": "Boardgame mo hinh", "parent": "do-choi-giai-tri", "description": "Danh muc boardgame va mo hinh lap rap cho giai tri nhom va suu tam.", "image_url": "https://picsum.photos/seed/boardgame-mo-hinh/1200/800", "sort_order": 30},
    {"slug": "cham-soc-thu-cung", "name": "Cham soc thu cung", "parent": None, "description": "Nhom product thuc an va phu kien co ban cho cho, meo va thu cung trong nha.", "image_url": "https://picsum.photos/seed/cham-soc-thu-cung/1200/800", "sort_order": 31},
    {"slug": "thuc-an-thu-cung", "name": "Thuc an thu cung", "parent": "cham-soc-thu-cung", "description": "Danh muc hat, pate va thuc an dong goi cho cho meo o nhieu giai doan.", "image_url": "https://picsum.photos/seed/thuc-an-thu-cung/1200/800", "sort_order": 32},
    {"slug": "phu-kien-thu-cung", "name": "Phu kien thu cung", "parent": "cham-soc-thu-cung", "description": "Danh muc day dan, cat ve sinh va vat dung giup cham soc thu cung sach se va an toan.", "image_url": "https://picsum.photos/seed/phu-kien-thu-cung/1200/800", "sort_order": 33},
]

DEMO_PRODUCT_TYPES = {
    "dien-thoai-va-may-tinh-bang": {"code": "ELECTRONIC_DEVICE", "name": "Electronic Device", "description": "Dong smartphone va tablet phuc vu lien lac, giai tri va xu ly cong viec di dong."},
    "phu-kien-cong-nghe": {"code": "TECH_ACCESSORY", "name": "Tech Accessory", "description": "Dong phu kien sac, am thanh va mo rong trai nghiem cho thiet bi so."},
    "thoi-trang-nam": {"code": "MEN_FASHION", "name": "Men Fashion", "description": "Dong trang phuc nam de mac, de phoi va phu hop nhip song hang ngay."},
    "thoi-trang-nu": {"code": "WOMEN_FASHION", "name": "Women Fashion", "description": "Dong trang phuc nu thanh lich cho cong so, dao pho va su kien nhe."},
    "cham-soc-da": {"code": "SKINCARE", "name": "Skincare", "description": "Dong serum, kem duong va cham soc da cho routine ca nhan sang toi."},
    "trang-diem": {"code": "MAKEUP", "name": "Makeup", "description": "Dong san pham makeup co ban, de dung cho phong cach tu nhien den noi bat."},
    "do-bep": {"code": "KITCHENWARE", "name": "Kitchenware", "description": "Dong do bep va dung cu nau an giup viec vao bep nhanh va tien loi hon."},
    "trang-tri-nha-cua": {"code": "HOME_DECOR", "name": "Home Decor", "description": "Dong vat dung trang tri cho phong khach, phong ngu va goc lam viec."},
    "do-so-sinh": {"code": "NEWBORN_ESSENTIAL", "name": "Newborn Essential", "description": "Dong do dung mem mai va an toan cho tre so sinh va me moi."},
    "sua-va-bim": {"code": "BABY_DAILY_CARE", "name": "Baby Daily Care", "description": "Dong sua, bim va san pham tieu hao thiet yeu cho be moi ngay."},
    "do-tap-luyen": {"code": "FITNESS_GEAR", "name": "Fitness Gear", "description": "Dong dung cu tap luyen tai nha phuc vu yoga, cardio va tang suc manh."},
    "da-ngoai-cam-trai": {"code": "OUTDOOR_CAMPING", "name": "Outdoor Camping", "description": "Dong do da ngoai va cam trai cho chuyen di cuoi tuan gon nhe va tien dung."},
    "sach-ky-nang": {"code": "SKILL_BOOK", "name": "Skill Book", "description": "Dong sach ky nang, tai chinh va phat trien ban than de hoc tap lien tuc."},
    "van-phong-pham": {"code": "STATIONERY", "name": "Stationery", "description": "Dong so tay, but viet va do dung hoc tap cho ban hoc va ban lam viec."},
    "do-an-vat": {"code": "SNACK", "name": "Snack", "description": "Dong snack va do an nhe phu hop bo sung nang luong nhanh trong ngay."},
    "do-uong-pha-san": {"code": "READY_DRINK", "name": "Ready Drink", "description": "Dong ca phe, tra va thuc uong pha nhanh cho nhu cau tiep nang luong."},
    "vitamin-bo-sung": {"code": "SUPPLEMENT", "name": "Supplement", "description": "Dong vitamin va thuc pham bo sung ho tro suc khoe va phuc hoi co the."},
    "cham-soc-ca-nhan": {"code": "PERSONAL_CARE", "name": "Personal Care", "description": "Dong san pham cham soc ca nhan va thiet bi nho phuc vu ve sinh moi ngay."},
    "do-choi-giao-duc": {"code": "EDUCATIONAL_TOY", "name": "Educational Toy", "description": "Dong do choi hoc tap giup tre phat trien tri tuong tuong va ky nang co ban."},
    "boardgame-mo-hinh": {"code": "BOARDGAME_MODEL", "name": "Boardgame Model", "description": "Dong boardgame va mo hinh giai tri cho ca nhan, ban be va gia dinh."},
    "thuc-an-thu-cung": {"code": "PET_FOOD", "name": "Pet Food", "description": "Dong thuc an kho, uot va bo sung cho cho meo o nhieu lua tuoi."},
    "phu-kien-thu-cung": {"code": "PET_ACCESSORY", "name": "Pet Accessory", "description": "Dong phu kien giup cham soc, di dao va giu khong gian song sach cho thu cung."},
}

DEMO_BRANDS = {
    "dien-tu": {"name": "Dien tu", "description": "Nhom product cho thiet bi so va phu kien cong nghe ban chay tai storefront."},
    "thoi-trang": {"name": "Thoi trang", "description": "Nhom product trang phuc co ban cho nam va nu theo nhu cau mac dep hang ngay."},
    "my-pham": {"name": "My pham", "description": "Nhom product cham soc da va trang diem phuc vu routine lam dep ca nhan."},
    "nha-cua-doi-song": {"name": "Nha cua doi song", "description": "Nhom product gia dung va trang tri cho can ho, phong ngu va phong bep."},
    "me-va-be": {"name": "Me va be", "description": "Nhom product do dung cho be nho va vat pham tieu hao phuc vu gia dinh tre."},
    "the-thao-da-ngoai": {"name": "The thao da ngoai", "description": "Nhom product tap luyen, trekking va cam trai cho nguoi yeu van dong."},
    "sach-van-phong-pham": {"name": "Sach van phong pham", "description": "Nhom product hoc tap va lam viec gom sach ky nang, so tay va but viet."},
    "thuc-pham-do-uong": {"name": "Thuc pham do uong", "description": "Nhom product snack va thuc uong dong goi cho nha o va van phong."},
    "suc-khoe-ca-nhan": {"name": "Suc khoe ca nhan", "description": "Nhom product vitamin, bo sung va cham soc co the moi ngay."},
    "do-choi-giai-tri": {"name": "Do choi giai tri", "description": "Nhom product boardgame, mo hinh va do choi giao duc cho tre nho va gia dinh."},
    "cham-soc-thu-cung": {"name": "Cham soc thu cung", "description": "Nhom product thuc an, day dan va vat dung thiet yeu cho cho meo."},
}

DEMO_CATEGORY_CONTENT = {
    "dien-thoai-va-may-tinh-bang": {"audience": "nguoi dung can lien lac, hoc tap va lam viec tren thiet bi di dong", "use_case": "giai tri, hoc online, chup anh va xu ly cong viec co ban", "feature_tags": ["portable", "connected", "daily-use", "screen"], "price_tier": "entry-to-premium", "collection": "digital-daily"},
    "phu-kien-cong-nghe": {"audience": "nguoi dung muon bo sung pin, am thanh va ket noi cho thiet bi so", "use_case": "sac nhanh, nghe nhac, du phong nang luong va phu tro di chuyen", "feature_tags": ["charging", "audio", "portable", "ecosystem"], "price_tier": "entry-to-mid", "collection": "smart-accessory"},
    "thoi-trang-nam": {"audience": "nguoi can trang phuc co ban cho di hoc, di lam va dao pho", "use_case": "mac hang ngay, di lam va phoi do toi gian", "feature_tags": ["basic-wear", "easy-match", "daily-style", "comfort"], "price_tier": "entry-to-mid", "collection": "mens-daily"},
    "thoi-trang-nu": {"audience": "nguoi muon xay dung tu do cho cong so va cuoc hen cuoi tuan", "use_case": "cong so, dao pho va trang phuc thanh lich", "feature_tags": ["minimal", "office", "soft-tone", "feminine"], "price_tier": "entry-to-mid", "collection": "womens-edit"},
    "cham-soc-da": {"audience": "nguoi bat dau hoac duy tri routine cham soc da ca nhan", "use_case": "duong am, phuc hoi va lam sang da", "feature_tags": ["hydrating", "barrier", "serum", "routine"], "price_tier": "entry-to-premium", "collection": "skin-routine"},
    "trang-diem": {"audience": "nguoi can makeup nhanh gon cho di lam va di choi", "use_case": "makeup tu nhien, tien loi va de dem theo", "feature_tags": ["glow", "longwear", "daily-makeup", "compact"], "price_tier": "entry-to-mid", "collection": "makeup-pouch"},
    "do-bep": {"audience": "gia dinh nho va nguoi o mot minh can do bep de dung", "use_case": "nau an nhanh, chuan bi bua an va tiet kiem thoi gian", "feature_tags": ["easy-clean", "kitchen", "time-saving", "home-cooking"], "price_tier": "entry-to-mid", "collection": "kitchen-helper"},
    "trang-tri-nha-cua": {"audience": "nguoi muon sap xep va lam dep can phong song", "use_case": "decor, toi uu khong gian va tang cam giac am cung", "feature_tags": ["cozy", "decor", "organize", "home-style"], "price_tier": "entry-to-mid", "collection": "cozy-home"},
    "do-so-sinh": {"audience": "gia dinh co em be trong giai doan so sinh den 12 thang", "use_case": "giu am, lau rua va cham soc em be hang ngay", "feature_tags": ["soft", "baby-safe", "cotton", "newborn"], "price_tier": "entry-to-mid", "collection": "baby-first"},
    "sua-va-bim": {"audience": "phu huynh can san pham tieu hao cho be su dung lien tuc", "use_case": "bo sung dinh duong va cham soc sinh hoat hang ngay cho be", "feature_tags": ["nutrition", "baby-care", "daily-use", "family"], "price_tier": "entry-to-high", "collection": "baby-daily"},
    "do-tap-luyen": {"audience": "nguoi tap tai nha hoac bat dau xay dung thoi quen van dong", "use_case": "yoga, cardio, tang suc manh co ban", "feature_tags": ["fitness", "home-workout", "flexible", "training"], "price_tier": "entry-to-mid", "collection": "move-at-home"},
    "da-ngoai-cam-trai": {"audience": "nguoi thich di da ngoai, trekking va picnic cuoi tuan", "use_case": "cam trai, picnic va di chuyen duong ngan", "feature_tags": ["camping", "portable", "outdoor", "weekend-trip"], "price_tier": "entry-to-mid", "collection": "weekend-outdoor"},
    "sach-ky-nang": {"audience": "nguoi di hoc va di lam can bo sung kien thuc thuc tien", "use_case": "doc sach phat trien ban than, giao tiep va tai chinh ca nhan", "feature_tags": ["learning", "self-growth", "mindset", "career"], "price_tier": "entry", "collection": "lifelong-learning"},
    "van-phong-pham": {"audience": "hoc sinh, sinh vien va nhan vien van phong can do dung ghi chu", "use_case": "viet, lap ke hoach va sap xep cong viec", "feature_tags": ["planner", "study", "writing", "desk"], "price_tier": "entry", "collection": "desk-setup"},
    "do-an-vat": {"audience": "nguoi can bua phu nho va mon an vat de dung trong ngay", "use_case": "an nhe, tiep nang luong va mang theo khi di lam", "feature_tags": ["snack", "quick-energy", "packaged", "daily"], "price_tier": "entry", "collection": "snack-corner"},
    "do-uong-pha-san": {"audience": "nguoi can thuc uong pha nhanh tai nha va van phong", "use_case": "pha ca phe, pha tra va thu gian giua ngay", "feature_tags": ["coffee", "tea", "instant", "office"], "price_tier": "entry", "collection": "drink-station"},
    "vitamin-bo-sung": {"audience": "nguoi muon bo sung vi chat va ho tro muc tieu suc khoe", "use_case": "bo sung vitamin, collagen va cham soc co the tu ben trong", "feature_tags": ["wellness", "supplement", "nutrition", "daily-care"], "price_tier": "mid", "collection": "healthy-habit"},
    "cham-soc-ca-nhan": {"audience": "nguoi uu tien ve sinh va cham soc co the moi ngay", "use_case": "ve sinh rang mieng, cham soc ca nhan va theo doi suc khoe co ban", "feature_tags": ["hygiene", "routine", "care", "wellbeing"], "price_tier": "entry-to-mid", "collection": "personal-routine"},
    "do-choi-giao-duc": {"audience": "tre em va gia dinh muon hoc qua tro choi", "use_case": "nhan dien mau sac, ky tu va phat trien tu duy logic", "feature_tags": ["learning", "kids", "creative", "hands-on"], "price_tier": "entry-to-mid", "collection": "smart-play"},
    "boardgame-mo-hinh": {"audience": "ban be, gia dinh va nguoi thich do choi giai tri co tinh suu tam", "use_case": "giai tri nhom, lap rap va ket noi ban be", "feature_tags": ["group-play", "strategy", "collectible", "fun"], "price_tier": "entry-to-mid", "collection": "family-fun"},
    "thuc-an-thu-cung": {"audience": "chu nuoi cho meo can khau phan on dinh va de bao quan", "use_case": "bo sung bua an chinh va doi bua tien loi cho thu cung", "feature_tags": ["pet-food", "nutrition", "daily-feed", "pet-care"], "price_tier": "entry-to-mid", "collection": "pet-daily"},
    "phu-kien-thu-cung": {"audience": "nguoi nuoi thu cung can do dung di dao, ve sinh va cham soc", "use_case": "di dao, giu sach khu vuc song va ho tro sinh hoat cho thu cung", "feature_tags": ["pet-accessory", "walking", "cleaning", "safety"], "price_tier": "entry-to-mid", "collection": "pet-home"},
}

DEMO_PRODUCTS = [
    ("smartphone-nova-5g", "Smartphone Nova 5G", "dien-thoai-va-may-tinh-bang", "dien-tu", 8990000, True),
    ("tablet-flex-note-11", "Tablet Flex Note 11", "dien-thoai-va-may-tinh-bang", "dien-tu", 11990000, False),
    ("pin-du-phong-fastcharge-20000", "Pin du phong FastCharge 20000mAh", "phu-kien-cong-nghe", "dien-tu", 790000, True),
    ("tai-nghe-airbass-pro", "Tai nghe AirBass Pro", "phu-kien-cong-nghe", "dien-tu", 1490000, False),
    ("ao-polo-nam-everyday", "Ao polo nam Everyday", "thoi-trang-nam", "thoi-trang", 390000, True),
    ("quan-jeans-nam-slimfit", "Quan jeans nam Slimfit", "thoi-trang-nam", "thoi-trang", 590000, False),
    ("dam-midi-thanh-lich", "Dam midi Thanh lich", "thoi-trang-nu", "thoi-trang", 690000, True),
    ("ao-blazer-nu-minimal", "Ao blazer nu Minimal", "thoi-trang-nu", "thoi-trang", 890000, False),
    ("serum-vitamin-c-30ml", "Serum Vitamin C 30ml", "cham-soc-da", "my-pham", 329000, True),
    ("kem-duong-phuc-hoi-barrier", "Kem duong phuc hoi Barrier", "cham-soc-da", "my-pham", 459000, False),
    ("cushion-natural-glow", "Cushion Natural Glow", "trang-diem", "my-pham", 349000, True),
    ("son-tint-velvet-rose", "Son tint Velvet Rose", "trang-diem", "my-pham", 219000, False),
    ("noi-chien-khong-dau-6l", "Noi chien khong dau 6L", "do-bep", "nha-cua-doi-song", 1690000, True),
    ("chao-chong-dinh-28cm", "Chao chong dinh 28cm", "do-bep", "nha-cua-doi-song", 420000, False),
    ("den-ngu-cam-ung", "Den ngu cam ung", "trang-tri-nha-cua", "nha-cua-doi-song", 350000, True),
    ("ke-sach-go-4-tang", "Ke sach go 4 tang", "trang-tri-nha-cua", "nha-cua-doi-song", 990000, False),
    ("body-suit-so-sinh-cotton", "Body suit so sinh Cotton", "do-so-sinh", "me-va-be", 199000, True),
    ("khan-sua-huu-co-4-lop", "Khan sua huu co 4 lop", "do-so-sinh", "me-va-be", 149000, False),
    ("ta-dan-m48", "Ta dan M48", "sua-va-bim", "me-va-be", 389000, True),
    ("sua-cong-thuc-so-2-800g", "Sua cong thuc so 2 800g", "sua-va-bim", "me-va-be", 515000, False),
    ("tham-yoga-tpe", "Tham yoga TPE", "do-tap-luyen", "the-thao-da-ngoai", 490000, True),
    ("bo-ta-tay-dieu-chinh-10kg", "Bo ta tay dieu chinh 10kg", "do-tap-luyen", "the-thao-da-ngoai", 890000, False),
    ("leu-cam-trai-4-nguoi", "Leu cam trai 4 nguoi", "da-ngoai-cam-trai", "the-thao-da-ngoai", 1590000, True),
    ("binh-giu-nhiet-da-ngoai-1l", "Binh giu nhiet da ngoai 1L", "da-ngoai-cam-trai", "the-thao-da-ngoai", 290000, False),
    ("sach-ky-nang-giao-tiep", "Sach Ky nang giao tiep", "sach-ky-nang", "sach-van-phong-pham", 129000, True),
    ("sach-tai-chinh-ca-nhan", "Sach Tai chinh ca nhan", "sach-ky-nang", "sach-van-phong-pham", 149000, False),
    ("so-tay-planner-a5", "So tay Planner A5", "van-phong-pham", "sach-van-phong-pham", 89000, True),
    ("but-gel-premium-10-mau", "But gel Premium 10 mau", "van-phong-pham", "sach-van-phong-pham", 65000, False),
    ("hat-dinh-duong-mix-500g", "Hat dinh duong mix 500g", "do-an-vat", "thuc-pham-do-uong", 165000, True),
    ("rong-bien-say-gion-12-goi", "Rong bien say gion 12 goi", "do-an-vat", "thuc-pham-do-uong", 99000, False),
    ("ca-phe-rang-xay-house-blend", "Ca phe rang xay House Blend", "do-uong-pha-san", "thuc-pham-do-uong", 185000, True),
    ("tra-dao-say-lanh-20-goi", "Tra dao say lanh 20 goi", "do-uong-pha-san", "thuc-pham-do-uong", 119000, False),
    ("vitamin-c-1000mg-60-vien", "Vitamin C 1000mg 60 vien", "vitamin-bo-sung", "suc-khoe-ca-nhan", 269000, True),
    ("collagen-peptide-5000mg", "Collagen Peptide 5000mg", "vitamin-bo-sung", "suc-khoe-ca-nhan", 399000, False),
    ("ban-chai-dien-sonic", "Ban chai dien Sonic", "cham-soc-ca-nhan", "suc-khoe-ca-nhan", 690000, True),
    ("may-do-huyet-ap-mini", "May do huyet ap Mini", "cham-soc-ca-nhan", "suc-khoe-ca-nhan", 790000, False),
    ("bo-xep-hinh-sang-tao-120", "Bo xep hinh sang tao 120 chi tiet", "do-choi-giao-duc", "do-choi-giai-tri", 259000, True),
    ("bang-hoc-chu-cai-nam-cham", "Bang hoc chu cai nam cham", "do-choi-giao-duc", "do-choi-giai-tri", 189000, False),
    ("boardgame-chien-thuat-gia-dinh", "Boardgame chien thuat gia dinh", "boardgame-mo-hinh", "do-choi-giai-tri", 449000, True),
    ("mo-hinh-lap-rap-xe-dua", "Mo hinh lap rap xe dua", "boardgame-mo-hinh", "do-choi-giai-tri", 329000, False),
    ("hat-cho-meo-truong-thanh-15kg", "Hat cho meo truong thanh 1.5kg", "thuc-an-thu-cung", "cham-soc-thu-cung", 215000, True),
    ("pate-cho-cho-vi-ga-12-goi", "Pate cho cho vi ga 12 goi", "thuc-an-thu-cung", "cham-soc-thu-cung", 175000, False),
    ("day-dan-phan-quang-cho-cho", "Day dan phan quang cho cho", "phu-kien-thu-cung", "cham-soc-thu-cung", 129000, True),
    ("cat-ve-sinh-huu-co-10l", "Cat ve sinh huu co 10L", "phu-kien-thu-cung", "cham-soc-thu-cung", 189000, False),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class SeedState:
    users: Dict[str, str] = field(default_factory=dict)
    products: List[Dict[str, Any]] = field(default_factory=list)
    carts: List[str] = field(default_factory=list)
    orders: List[str] = field(default_factory=list)
    inventory_items: List[str] = field(default_factory=list)
    ai_docs: List[str] = field(default_factory=list)
    ai_events_count: int = 0


class TechShopSeeder:
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.state = SeedState()
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ------------------------
    # Helpers
    # ------------------------
    def _request(
        self,
        method: str,
        service: str,
        path: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
    ) -> requests.Response:
        url = f"{SERVICE_URLS[service]}{path}"
        merged_headers = dict(self.session.headers)
        if headers:
            merged_headers.update(headers)

        if self.verbose:
            logger.debug("%s %s payload=%s", method.upper(), url, json_payload)

        if self.dry_run:
            class DummyResponse:
                status_code = 200

                @staticmethod
                def json() -> Dict[str, Any]:
                    return {}

                text = ""

            return DummyResponse()  # type: ignore[return-value]

        return self.session.request(
            method=method.upper(),
            url=url,
            headers=merged_headers,
            json=json_payload,
            timeout=timeout,
        )

    def _run_cmd(self, args: List[str]) -> Tuple[bool, str]:
        cmd_text = " ".join(args)
        logger.debug("RUN: %s", cmd_text)
        if self.dry_run:
            return True, f"[DRY-RUN] {cmd_text}"

        proc = subprocess.run(
            args,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, out.strip()

    def _run_docker_manage(self, service: str, manage_args: List[str]) -> Tuple[bool, str]:
        return self._run_cmd(
            ["docker", "compose", "exec", "-T", service, "python", "manage.py", *manage_args]
        )

    def _run_docker_shell(self, service: str, python_code: str) -> Tuple[bool, str]:
        cmd = ["docker", "compose", "exec", "-T", service, "python", "manage.py", "shell"]
        logger.debug("RUN: %s <stdin>", " ".join(cmd))
        if self.dry_run:
            return True, f"[DRY-RUN] {' '.join(cmd)} <stdin>"

        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            input=python_code,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, out.strip()

    def _ensure_app_migrated(self, service: str, app_label: str) -> bool:
        """Ensure a Django app has migrations generated and applied."""
        show_ok, show_output = self._run_docker_manage(service, ["showmigrations", app_label])
        if not show_ok:
            logger.warning("  ✗ Could not inspect %s migrations: %s", app_label, show_output)
            return False

        if "no migrations" in show_output.lower():
            logger.info("  ! %s app has no migrations, generating with makemigrations...", app_label)
            mk_ok, mk_output = self._run_docker_manage(service, ["makemigrations", app_label])
            if not mk_ok:
                logger.warning("  ✗ makemigrations %s failed: %s", app_label, mk_output)
                return False

        migrate_ok, migrate_output = self._run_docker_manage(service, ["migrate", app_label])
        if not migrate_ok:
            logger.warning("  ✗ migrate %s failed: %s", app_label, migrate_output)
            return False
        return True

    @staticmethod
    def _extract_data(resp: requests.Response) -> Dict[str, Any]:
        try:
            payload = resp.json()
            if isinstance(payload, dict):
                return payload.get("data", {}) if "data" in payload else payload
        except Exception:
            pass
        return {}

    # ------------------------
    # Orchestration
    # ------------------------
    def seed_all(self) -> bool:
        logger.info("=" * 80)
        logger.info("STARTING COMPLETE SYSTEM SEED")
        logger.info("Dry Run: %s | Verbose: %s", self.dry_run, self.verbose)
        logger.info("=" * 80)

        ok = True
        ok = self.seed_users() and ok
        ok = self.seed_product_catalog() and ok
        ok = self.seed_inventory() and ok
        ok = self.seed_carts() and ok
        ok = self.seed_orders_and_payments() and ok
        ok = self.seed_ai_knowledge_base() and ok
        ok = self.seed_ai_events() and ok
        self.print_summary()
        return ok

    # ------------------------
    # Phase 1: Users
    # ------------------------
    def seed_users(self) -> bool:
        logger.info("\n[PHASE 1] Seeding Users...")

        # Ensure demo users exist by calling register (idempotent-ish).
        for user in DEMO_USERS:
            payload = {
                "email": user["email"],
                "full_name": user["full_name"],
                "password": DEMO_PASSWORD,
                "confirm_password": DEMO_PASSWORD,
                "phone_number": user["phone_number"],
            }
            try:
                resp = self._request("post", "user", "/api/v1/auth/register/", json_payload=payload)
                if resp.status_code in (200, 201):
                    logger.info("  ✓ Registered: %s", user["email"])
                elif resp.status_code in (400, 409):
                    logger.info("  ✓ Exists: %s", user["email"])
                else:
                    logger.warning("  ✗ Register %s failed: %s", user["email"], resp.status_code)
            except Exception as exc:
                logger.warning("  ✗ Register %s error: %s", user["email"], exc)

        # Resolve user IDs via login.
        candidate_passwords = {
            "admin@example.com": [DEMO_PASSWORD, "admin123"],
            "staff@example.com": [DEMO_PASSWORD, "staff123"],
            "john@example.com": [DEMO_PASSWORD, "john123"],
            "jane@example.com": [DEMO_PASSWORD, "jane123"],
        }

        for user in DEMO_USERS:
            email = user["email"]
            resolved = False
            for pwd in candidate_passwords.get(email, [DEMO_PASSWORD]):
                try:
                    resp = self._request(
                        "post",
                        "user",
                        "/api/v1/auth/login/",
                        json_payload={"email": email, "password": pwd},
                    )
                    if resp.status_code == 200:
                        data = self._extract_data(resp)
                        user_id = (data.get("user") or {}).get("id")
                        if user_id:
                            self.state.users[email] = user_id
                            logger.info("  ✓ User ID resolved: %s -> %s", email, user_id)
                            resolved = True
                            break
                except Exception:
                    continue

            if not resolved:
                logger.warning("  ✗ Could not resolve user ID for %s", email)

        role_code = """
from modules.identity.infrastructure.models import User

targets = {
    "admin@example.com": ("admin", True),
    "staff@example.com": ("staff", True),
    "john@example.com": ("customer", False),
    "jane@example.com": ("customer", False),
}
for email, (role, is_staff) in targets.items():
    user = User.objects.filter(email=email).first()
    if not user:
        continue
    changed = False
    if user.role != role:
        user.role = role
        changed = True
    if user.is_staff != is_staff:
        user.is_staff = is_staff
        changed = True
    if not user.is_verified:
        user.is_verified = True
        changed = True
    if changed:
        user.save(update_fields=["role", "is_staff", "is_verified"])
        print("updated", email, role)
    else:
        print("ok", email, role)
""".strip()
        role_ok, role_output = self._run_docker_shell("user_service", role_code)
        if role_ok:
            logger.info("  ✓ User roles normalized for demo accounts")
        else:
            logger.warning("  ✗ Could not normalize user roles: %s", role_output)

        return len(self.state.users) >= 2

    # ------------------------
    # Phase 2-5: Product catalog
    # ------------------------
    def seed_product_catalog(self) -> bool:
        logger.info("\n[PHASE 2-5] Seeding Product Catalog...")

        # product_service currently lacks stable create APIs in this repo state,
        # so we seed using manage.py shell in container.
        code = f"""
from django.utils import timezone
from modules.catalog.infrastructure.models import CategoryModel, BrandModel, ProductTypeModel, ProductModel, ProductVariantModel

category_tree = {repr(DEMO_CATEGORY_TREE)}
categories = {{}}
public_products = ProductModel.objects.filter(
    status="active",
    is_active=True,
    published_at__isnull=False,
)
for item in category_tree:
    parent = categories.get(item["parent"]) if item.get("parent") else None
    c, _ = CategoryModel.objects.get_or_create(
        slug=item["slug"],
        defaults={{
            "name": item["name"],
            "parent": parent,
            "description": item["description"],
            "image_url": item["image_url"],
            "is_active": True,
            "sort_order": item["sort_order"],
        }},
    )
    changed = False
    if c.name != item["name"]:
        c.name = item["name"]; changed = True
    if c.parent_id != (parent.id if parent else None):
        c.parent = parent; changed = True
    if c.description != item["description"]:
        c.description = item["description"]; changed = True
    if c.image_url != item["image_url"]:
        c.image_url = item["image_url"]; changed = True
    if c.sort_order != item["sort_order"]:
        c.sort_order = item["sort_order"]; changed = True
    if not c.is_active:
        c.is_active = True; changed = True
    if changed:
        c.save()
    categories[item["slug"]] = c

desired_category_slugs = {{item["slug"] for item in category_tree}}
for extra_category in CategoryModel.objects.exclude(slug__in=desired_category_slugs):
    if extra_category.is_active and not public_products.filter(category=extra_category).exists() and not extra_category.children.filter(is_active=True).exists():
        extra_category.is_active = False
        extra_category.save(update_fields=["is_active"])

brands = {repr(DEMO_BRANDS)}
brand_objs = {{}}
for slug, info in brands.items():
    b, _ = BrandModel.objects.get_or_create(
        slug=slug,
        defaults={{
            "name": info["name"],
            "description": info["description"],
            "logo_url": f"https://picsum.photos/seed/brand-{{slug}}/400/400",
            "is_active": True,
        }},
    )
    changed = False
    if b.name != info["name"]:
        b.name = info["name"]; changed = True
    if b.description != info["description"]:
        b.description = info["description"]; changed = True
    desired_logo = f"https://picsum.photos/seed/brand-{{slug}}/400/400"
    if b.logo_url != desired_logo:
        b.logo_url = desired_logo; changed = True
    if not b.is_active:
        b.is_active = True; changed = True
    if changed:
        b.save()
    brand_objs[slug] = b

items = {repr(DEMO_PRODUCTS)}
type_map = {repr(DEMO_PRODUCT_TYPES)}
content_map = {repr(DEMO_CATEGORY_CONTENT)}
product_types = {{}}
for category_slug, info in type_map.items():
    pt, _ = ProductTypeModel.objects.get_or_create(
        code=info["code"],
        defaults={{"name": info["name"], "description": info["description"], "is_active": True}},
    )
    changed = False
    if pt.name != info["name"]:
        pt.name = info["name"]; changed = True
    if pt.description != info["description"]:
        pt.description = info["description"]; changed = True
    if not pt.is_active:
        pt.is_active = True; changed = True
    if changed:
        pt.save()
    product_types[category_slug] = pt

desired_type_codes = {{info["code"] for info in type_map.values()}}
for extra_type in ProductTypeModel.objects.exclude(code__in=desired_type_codes):
    if extra_type.is_active and not public_products.filter(product_type=extra_type).exists():
        extra_type.is_active = False
        extra_type.save(update_fields=["is_active"])

for idx, (slug, name, category_slug, brand_slug, price, featured) in enumerate(items, start=1):
    category_meta = content_map[category_slug]
    brand = brand_objs[brand_slug]
    category = categories[category_slug]
    product_type = product_types[category_slug]
    short_description = f"{{product_type.name}} {{brand.name}} phu hop cho {{category_meta['audience']}}."
    description = (
        f"{{name}} thuoc danh muc {{category.name}}. "
        f"San pham phuc vu {{category_meta['use_case']}} va nam trong bo suu tap {{category_meta['collection']}}. "
        f"Cac diem nhan chinh: {{', '.join(category_meta['feature_tags'])}}."
    )
    attributes = {{
        "category_slug": category_slug,
        "brand_slug": brand_slug,
        "product_type_code": product_type.code,
        "demo_collection": category_meta["collection"],
        "target_audience": category_meta["audience"],
        "primary_use_case": category_meta["use_case"],
        "feature_tags": category_meta["feature_tags"],
        "price_tier": category_meta["price_tier"],
    }}
    seo_title = f"{{name}} | {{category.name}} {{brand.name}}"
    seo_description = f"Kham pha {{name}} trong danh muc {{category.name}} - toi uu cho {{category_meta['use_case']}}."
    thumbnail_url = f"https://picsum.photos/seed/{{slug}}/800/600"
    p, _ = ProductModel.objects.get_or_create(
        slug=slug,
        defaults={{
            "name": name,
            "short_description": short_description,
            "description": description,
            "category": category,
            "brand": brand,
            "product_type": product_type,
            "base_price": price,
            "currency": "VND",
            "attributes": attributes,
            "status": "active",
            "is_active": True,
            "is_featured": featured,
            "thumbnail_url": thumbnail_url,
            "seo_title": seo_title,
            "seo_description": seo_description,
            "published_at": timezone.now(),
        }},
    )
    changed = False
    if p.name != name:
        p.name = name; changed = True
    if p.short_description != short_description:
        p.short_description = short_description; changed = True
    if p.description != description:
        p.description = description; changed = True
    if p.status != "active":
        p.status = "active"; changed = True
    if not p.is_active:
        p.is_active = True; changed = True
    if p.published_at is None:
        p.published_at = timezone.now(); changed = True
    if str(p.category.slug) != category_slug:
        p.category = category; changed = True
    if p.brand_id != brand.id:
        p.brand = brand; changed = True
    if p.product_type_id != product_type.id:
        p.product_type = product_type; changed = True
    if float(p.base_price) != float(price):
        p.base_price = price; changed = True
    if p.attributes != attributes:
        p.attributes = attributes; changed = True
    if p.is_featured != featured:
        p.is_featured = featured; changed = True
    if p.thumbnail_url != thumbnail_url:
        p.thumbnail_url = thumbnail_url; changed = True
    if p.seo_title != seo_title:
        p.seo_title = seo_title; changed = True
    if p.seo_description != seo_description:
        p.seo_description = seo_description; changed = True
    if changed:
        p.save()

    variant_sku = f"{{slug.upper()}}-STD"
    variant_barcode = f"BAR-{{slug.upper().replace('-', '')}}"
    variant, _ = ProductVariantModel.objects.get_or_create(
        sku=variant_sku,
        defaults={{
            "product": p,
            "name": "Standard",
            "is_default": True,
            "is_active": True,
            "price_override": price,
            "barcode": variant_barcode,
        }},
    )
    variant_changed = False
    if variant.product_id != p.id:
        variant.product = p; variant_changed = True
    if variant.name != "Standard":
        variant.name = "Standard"; variant_changed = True
    if not variant.is_default:
        variant.is_default = True; variant_changed = True
    if not variant.is_active:
        variant.is_active = True; variant_changed = True
    if float(variant.price_override or 0) != float(price):
        variant.price_override = price; variant_changed = True
    if variant.barcode != variant_barcode:
        variant.barcode = variant_barcode; variant_changed = True
    if variant_changed:
        variant.save()

desired_product_slugs = set()
for item in items:
    desired_product_slugs.add(item[0])
for extra_product in ProductModel.objects.exclude(slug__in=desired_product_slugs):
    changed = False
    if extra_product.status != "draft":
        extra_product.status = "draft"; changed = True
    if extra_product.is_active:
        extra_product.is_active = False; changed = True
    if extra_product.is_featured:
        extra_product.is_featured = False; changed = True
    if extra_product.published_at is not None:
        extra_product.published_at = None; changed = True
    if changed:
        extra_product.save()
    extra_product.variants.filter(is_active=True).update(is_active=False, is_default=False)

print("seeded_products", ProductModel.objects.filter(status="active", is_active=True, published_at__isnull=False).count())
""".strip()

        ok, output = self._run_docker_shell("product_service", code)
        if not ok:
            logger.error("  ✗ Product seed failed.\n%s", output)
            return False
        logger.info("  ✓ Product seed command completed")
        if self.verbose and output:
            logger.debug(output)

        # Refresh in-memory product list from public API.
        try:
            resp = self._request("get", "product", "/api/v1/catalog/products/?page_size=100")
            if resp.status_code == 200:
                payload = resp.json()
                self.state.products = payload.get("results", [])
                logger.info("  ✓ Public catalog count: %s", payload.get("count", 0))
            else:
                logger.warning("  ✗ Could not read product list: %s", resp.status_code)
        except Exception as exc:
            logger.warning("  ✗ Could not read product list: %s", exc)

        return len(self.state.products) > 0

    # ------------------------
    # Phase 6: Inventory
    # ------------------------
    def seed_inventory(self) -> bool:
        logger.info("\n[PHASE 6] Seeding Inventory...")
        self._ensure_app_migrated("inventory_service", "inventory")
        if not self.state.products:
            logger.warning("  ✗ No products available to seed inventory")
            return False

        admin_headers = {"X-Admin": "true"}
        created = 0

        for prod in self.state.products:
            product_id = prod.get("id")
            if not product_id:
                continue
            try:
                check = self._request(
                    "get",
                    "inventory",
                    f"/api/v1/admin/inventory/stock-items/?product_id={product_id}&limit=5",
                    headers=admin_headers,
                )
                exists = False
                if check.status_code == 200:
                    items = self._extract_data(check).get("items", [])
                    exists = len(items) > 0
                if exists:
                    continue

                create = self._request(
                    "post",
                    "inventory",
                    "/api/v1/admin/inventory/stock-items/",
                    headers=admin_headers,
                    json_payload={
                        "product_id": product_id,
                        "quantity": 40,
                        "warehouse_code": "MAIN",
                        "on_hand_quantity": 40,
                        "safety_stock": 5,
                    },
                )
                if create.status_code in (200, 201):
                    item_id = self._extract_data(create).get("id")
                    if item_id:
                        self.state.inventory_items.append(str(item_id))
                    created += 1
                else:
                    logger.debug("  Inventory create skipped for %s: %s", product_id, create.status_code)
            except Exception as exc:
                logger.debug("  Inventory error for %s: %s", product_id, exc)

        logger.info("  ✓ Inventory processed (new items: %s)", created)
        return True

    # ------------------------
    # Phase 7: Carts
    # ------------------------
    def seed_carts(self) -> bool:
        logger.info("\n[PHASE 7] Seeding Carts...")
        self._ensure_app_migrated("cart_service", "cart")
        john_id = self.state.users.get("john@example.com")
        jane_id = self.state.users.get("jane@example.com")
        if not john_id and not jane_id:
            logger.warning("  ✗ No customer users available for cart seed")
            return False
        if not self.state.products:
            logger.warning("  ✗ No products available for cart seed")
            return False

        def add_for_user(user_id: str, product_indexes: List[int]) -> None:
            headers = {"X-User-ID": user_id}
            for idx in product_indexes:
                if idx >= len(self.state.products):
                    continue
                p = self.state.products[idx]
                payload = {"product_id": p["id"], "quantity": 1}
                resp = self._request("post", "cart", "/api/v1/cart/items/", headers=headers, json_payload=payload)
                if resp.status_code not in (200, 201):
                    logger.debug("  add_item failed for user=%s product=%s: %s", user_id, p["id"], resp.status_code)

            current = self._request("get", "cart", "/api/v1/cart/current/", headers=headers)
            if current.status_code == 200:
                cart_data = self._extract_data(current)
                cart_id = cart_data.get("id")
                if cart_id:
                    self.state.carts.append(str(cart_id))

        if john_id:
            add_for_user(john_id, [0, 3])
            logger.info("  ✓ Cart seeded for john@example.com")
        if jane_id:
            add_for_user(jane_id, [1, 4])
            logger.info("  ✓ Cart seeded for jane@example.com")
        return True

    # ------------------------
    # Phase 8-10: Orders/Payments/Shipments
    # ------------------------
    def seed_orders_and_payments(self) -> bool:
        logger.info("\n[PHASE 8-10] Seeding Orders/Payments/Shipments...")
        john_id = self.state.users.get("john@example.com")
        jane_id = self.state.users.get("jane@example.com")
        if not (john_id and jane_id):
            logger.warning("  ✗ Missing John/Jane user IDs, skipping order seed")
            return False
        if len(self.state.products) < 2:
            logger.warning("  ✗ Not enough products, skipping order seed")
            return False

        order_seed_rows = [
            {
                "order_number": "ORD-SEED-001",
                "user_id": john_id,
                "status": "paid",
                "payment_status": "paid",
                "fulfillment_status": "preparing",
                "product": self.state.products[0],
                "qty": 1,
            },
            {
                "order_number": "ORD-SEED-002",
                "user_id": jane_id,
                "status": "shipping",
                "payment_status": "paid",
                "fulfillment_status": "shipped",
                "product": self.state.products[1],
                "qty": 1,
            },
        ]

        if not self._ensure_app_migrated("order_service", "order"):
            logger.warning("  ✗ Could not prepare order migrations, skipping order seed.")
            return True

        shell_payload = repr(order_seed_rows)
        code = f"""
import uuid
from decimal import Decimal
from django.utils import timezone
from modules.order.infrastructure.models import OrderModel, OrderItemModel, OrderStatusHistoryModel

rows = {shell_payload}
for row in rows:
    p = row["product"]
    qty = int(row["qty"])
    unit_price = Decimal(str(p.get("base_price", "0")))
    subtotal = unit_price * qty
    grand_total = subtotal + Decimal("30000")

    order, created = OrderModel.objects.get_or_create(
        order_number=row["order_number"],
        defaults={{
            "id": uuid.uuid4(),
            "user_id": row["user_id"],
            "cart_id": uuid.uuid4(),
            "status": row["status"],
            "payment_status": row["payment_status"],
            "fulfillment_status": row["fulfillment_status"],
            "currency": "VND",
            "subtotal_amount": subtotal,
            "shipping_fee_amount": Decimal("30000"),
            "discount_amount": Decimal("0"),
            "tax_amount": Decimal("0"),
            "grand_total_amount": grand_total,
            "total_quantity": qty,
            "item_count": 1,
            "customer_name_snapshot": "Demo Customer",
            "customer_email_snapshot": "demo@example.com",
            "customer_phone_snapshot": "0123456789",
            "receiver_name": "Demo Receiver",
            "receiver_phone": "0123456789",
            "shipping_line1": "123 Demo Street",
            "shipping_line2": "",
            "shipping_ward": "",
            "shipping_district": "District 1",
            "shipping_city": "Ho Chi Minh City",
            "shipping_country": "Vietnam",
            "shipping_postal_code": "",
            "notes": "Seeded by shared/scripts/seed_complete_system.py",
            "placed_at": timezone.now(),
            "paid_at": timezone.now() if row["payment_status"] == "paid" else None,
        }},
    )

    if created:
        OrderItemModel.objects.create(
            id=uuid.uuid4(),
            order=order,
            product_id=p["id"],
            variant_id=None,
            sku=f"{{p['slug'].upper()}}-STD",
            quantity=qty,
            unit_price=unit_price,
            line_total=subtotal,
            currency="VND",
            product_name_snapshot=p["name"],
            product_slug_snapshot=p["slug"],
            variant_name_snapshot="Standard",
            brand_name_snapshot=p.get("brand_name") or "",
            category_name_snapshot=p.get("category_name") or "",
            thumbnail_url_snapshot=p.get("thumbnail_url") or "",
            attributes_snapshot={{}},
        )
        OrderStatusHistoryModel.objects.create(
            id=uuid.uuid4(),
            order=order,
            from_status=None,
            to_status=row["status"],
            note="Seeded order",
            metadata={{"seed": True}},
        )
        print("created", order.order_number, order.id)
    else:
        print("exists", order.order_number, order.id)
""".strip()

        ok, output = self._run_docker_shell("order_service", code)
        if not ok:
            logger.warning("  ✗ Order seed skipped: %s", output)
            return True

        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) == 3 and parts[0] in {"created", "exists"}:
                self.state.orders.append(parts[2])
        logger.info("  ✓ Orders processed")
        return True

    # ------------------------
    # Phase 11: AI knowledge
    # ------------------------
    def seed_ai_knowledge_base(self) -> bool:
        logger.info("\n[PHASE 11] Seeding AI Knowledge Base...")
        docs = [
            {
                "title": "Shipping Policy",
                "document_type": "shipping_policy",
                "source": "seed_script",
                "content": "Free shipping for orders above 2,000,000 VND. Standard shipping 2-5 days.",
            },
            {
                "title": "Return Policy",
                "document_type": "return_policy",
                "source": "seed_script",
                "content": "Returns accepted within 30 days for unused items in original condition.",
            },
            {
                "title": "Payment Policy",
                "document_type": "payment_policy",
                "source": "seed_script",
                "content": "Accepted methods: card, bank transfer, and major e-wallets.",
            },
        ]

        created = 0
        for doc in docs:
            try:
                resp = self._request("post", "ai", "/api/v1/admin/ai/knowledge/", json_payload=doc)
                if resp.status_code in (200, 201):
                    doc_id = self._extract_data(resp).get("id")
                    if doc_id:
                        self.state.ai_docs.append(str(doc_id))
                    created += 1
                else:
                    logger.debug("  AI doc upsert skipped (%s): %s", doc["title"], resp.status_code)
            except Exception as exc:
                logger.debug("  AI doc error (%s): %s", doc["title"], exc)

        logger.info("  ✓ AI knowledge processed (new: %s)", created)
        return True

    # ------------------------
    # Phase 12: AI events
    # ------------------------
    def seed_ai_events(self) -> bool:
        logger.info("\n[PHASE 12] Seeding AI Behavioral Events...")
        if not self.state.products:
            logger.warning("  ✗ No products for AI events")
            return False

        john_id = self.state.users.get("john@example.com")
        jane_id = self.state.users.get("jane@example.com")
        if not (john_id or jane_id):
            logger.warning("  ✗ No users for AI events")
            return False

        events: List[Dict[str, Any]] = []
        for uid in [john_id, jane_id]:
            if not uid:
                continue
            for p in self.state.products[:4]:
                events.append(
                    {
                        "event_type": "product_view",
                        "user_id": uid,
                        "product_id": p["id"],
                        "brand_name": p.get("brand_name"),
                        "category_name": p.get("category_name"),
                        "price_amount": p.get("base_price"),
                        "source_service": "seed_script",
                        "metadata": {"seed": True},
                    }
                )

        try:
            resp = self._request(
                "post",
                "ai",
                "/api/v1/internal/ai/events/",
                json_payload={"events": events},
            )
            if resp.status_code in (200, 201):
                count = int(self._extract_data(resp).get("count", len(events)))
                self.state.ai_events_count = count
                logger.info("  ✓ AI events tracked: %s", count)
                return True
            logger.warning("  ✗ AI events failed: %s", resp.status_code)
            return False
        except Exception as exc:
            logger.warning("  ✗ AI events error: %s", exc)
            return False

    # ------------------------
    # Summary
    # ------------------------
    def print_summary(self) -> None:
        logger.info("\n" + "=" * 80)
        logger.info("SEEDING SUMMARY")
        logger.info("=" * 80)
        logger.info("Users resolved: %s", len(self.state.users))
        logger.info("Products available: %s", len(self.state.products))
        logger.info("Inventory items created: %s", len(self.state.inventory_items))
        logger.info("Carts prepared: %s", len(self.state.carts))
        logger.info("Orders prepared: %s", len(self.state.orders))
        logger.info("AI docs created: %s", len(self.state.ai_docs))
        logger.info("AI events tracked: %s", self.state.ai_events_count)
        if self.verbose:
            logger.debug("User IDs: %s", self.state.users)
        logger.info("=" * 80)
        logger.info("✓ SEEDING COMPLETE")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Master seed orchestration for TechShop microservices"
    )
    parser.add_argument("--clean", action="store_true", help="Reserved flag (not implemented)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without applying")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--users-only", action="store_true", help="Seed only users")
    parser.add_argument("--products-only", action="store_true", help="Seed only product catalog")
    parser.add_argument("--orders-only", action="store_true", help="Seed only orders phase")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Initializing TechShop Seeder...")
    logger.info("Services: %s", SERVICE_URLS)

    seeder = TechShopSeeder(dry_run=args.dry_run, verbose=args.verbose)

    if args.users_only:
        seeder.seed_users()
        seeder.print_summary()
        return
    if args.products_only:
        seeder.seed_product_catalog()
        seeder.seed_inventory()
        seeder.print_summary()
        return
    if args.orders_only:
        seeder.seed_users()
        seeder.seed_product_catalog()
        seeder.seed_orders_and_payments()
        seeder.print_summary()
        return

    success = seeder.seed_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
