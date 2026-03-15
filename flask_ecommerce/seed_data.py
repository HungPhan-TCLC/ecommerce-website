"""
seed_data.py - Tạo Mock Data cho Fashion E-commerce Store
Chạy file này để tạo database và điền dữ liệu mẫu.
Usage: python seed_data.py
"""

import os
import sys
from datetime import datetime, timedelta
import random

# Thiết lập Flask app context để sử dụng SQLAlchemy
from app import create_app
from models import db, User, Category, Product, Order, OrderItem, UserInteraction, CartItem
from werkzeug.security import generate_password_hash


def seed_categories():
    """Tạo các danh mục thời trang"""
    categories = [
        {"name": "Áo nam", "slug": "ao-nam", "description": "Áo thun, áo sơ mi, áo khoác nam"},
        {"name": "Quần nam", "slug": "quan-nam", "description": "Quần jeans, quần kaki, quần short nam"},
        {"name": "Áo nữ", "slug": "ao-nu", "description": "Áo kiểu, áo croptop, áo sơ mi nữ"},
        {"name": "Váy & Đầm", "slug": "vay-dam", "description": "Váy ngắn, đầm dạ hội, đầm công sở"},
        {"name": "Quần nữ", "slug": "quan-nu", "description": "Quần jeans, quần ống rộng, quần legging"},
        {"name": "Phụ kiện", "slug": "phu-kien", "description": "Túi xách, mắt kính, thắt lưng, mũ"},
        {"name": "Giày dép", "slug": "giay-dep", "description": "Giày sneaker, giày cao gót, sandal"},
    ]

    for cat_data in categories:
        cat = Category(**cat_data)
        db.session.add(cat)
    db.session.commit()
    print(f"[OK] Đã tạo {len(categories)} categories.")
    return Category.query.all()


def seed_products(categories):
    """Tạo 50 sản phẩm thời trang thực tế"""

    # Mapping category slug -> category object
    cat_map = {c.slug: c for c in categories}

    products_data = [
        # ==================== ÁO NAM (8 sản phẩm) ====================
        {
            "name": "Áo Thun Cotton Basic Trắng",
            "description": "Áo thun nam cổ tròn chất liệu cotton 100% mềm mại, thoáng mát. Thiết kế basic dễ phối đồ, phù hợp mặc hàng ngày hoặc layer bên trong áo khoác.",
            "price": 199000, "original_price": 299000,
            "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500",
            "category": "ao-nam", "tags": "basic,cotton,thoáng mát,cổ tròn,trắng,mùa hè",
            "gender": "nam", "material": "Cotton 100%", "style": "casual", "is_featured": True,
        },
        {
            "name": "Áo Sơ Mi Oxford Slim Fit",
            "description": "Áo sơ mi nam vải Oxford cao cấp, form Slim Fit tôn dáng. Cổ button-down lịch lãm, phù hợp đi làm và dự tiệc. Chống nhăn tốt.",
            "price": 450000, "original_price": 590000,
            "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500",
            "category": "ao-nam", "tags": "sơ mi,oxford,slim fit,công sở,lịch lãm,chống nhăn",
            "gender": "nam", "material": "Oxford Cotton", "style": "formal", "is_featured": True,
        },
        {
            "name": "Áo Polo Pique Classic",
            "description": "Áo polo nam chất liệu vải pique dệt kim thoáng khí. Logo thêu tinh tế trên ngực trái, cổ bẻ sang trọng. Phù hợp đi chơi golf hoặc dạo phố.",
            "price": 350000, "original_price": 450000,
            "image_url": "https://images.unsplash.com/photo-1586790170083-2f9ceadc732d?w=500",
            "category": "ao-nam", "tags": "polo,pique,cổ bẻ,thanh lịch,thể thao,golf",
            "gender": "nam", "material": "Cotton Pique", "style": "casual", "is_featured": False,
        },
        {
            "name": "Áo Khoác Bomber Jacket Đen",
            "description": "Áo khoác bomber jacket phong cách streetwear. Chất liệu polyester chống gió nhẹ, lớp lót mềm mại. Bo gấu và tay áo co giãn, khóa kéo YKK bền bỉ.",
            "price": 650000, "original_price": 850000,
            "image_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500",
            "category": "ao-nam", "tags": "bomber,jacket,streetwear,chống gió,đen,thu đông",
            "gender": "nam", "material": "Polyester", "style": "streetwear", "is_featured": True,
        },
        {
            "name": "Áo Hoodie Oversize Xám",
            "description": "Áo hoodie nam form oversize trẻ trung. Chất nỉ bông dày dặn, mũ trùm rộng, túi kangaroo phía trước. Giữ ấm tốt cho mùa đông.",
            "price": 420000, "original_price": 550000,
            "image_url": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=500",
            "category": "ao-nam", "tags": "hoodie,oversize,nỉ bông,giữ ấm,xám,thu đông",
            "gender": "nam", "material": "Cotton Fleece", "style": "streetwear", "is_featured": False,
        },
        {
            "name": "Áo Thun Graphic Art Print",
            "description": "Áo thun nam in hình nghệ thuật độc đáo. Cotton co giãn 4 chiều, bền màu sau nhiều lần giặt. Form regular fit thoải mái.",
            "price": 280000, "original_price": 380000,
            "image_url": "https://images.unsplash.com/photo-1503341504253-dff4f94032ef?w=500",
            "category": "ao-nam", "tags": "thun,graphic,nghệ thuật,cotton,in hình,trẻ trung",
            "gender": "nam", "material": "Cotton Spandex", "style": "casual", "is_featured": False,
        },
        {
            "name": "Áo Blazer Linen Xanh Navy",
            "description": "Áo blazer nam chất liệu linen mát mẻ, phong cách smart casual. Hai nút cài, hai túi hông nắp, túi ngực. Phù hợp mặc đi làm hoặc dự sự kiện.",
            "price": 890000, "original_price": 1200000,
            "image_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=500",
            "category": "ao-nam", "tags": "blazer,linen,smart casual,navy,công sở,sự kiện",
            "gender": "nam", "material": "Linen", "style": "formal", "is_featured": True,
        },
        {
            "name": "Áo Thun Henley Tay Dài",
            "description": "Áo thun henley nam tay dài, cổ mở 3 nút tạo điểm nhấn nam tính. Vải cotton pha spandex co giãn, thoải mái vận động.",
            "price": 320000, "original_price": None,
            "image_url": "https://images.unsplash.com/photo-1618517351616-38fb9c5210c6?w=500",
            "category": "ao-nam", "tags": "henley,tay dài,cotton,nam tính,basic,thu đông",
            "gender": "nam", "material": "Cotton Spandex", "style": "casual", "is_featured": False,
        },

        # ==================== QUẦN NAM (7 sản phẩm) ====================
        {
            "name": "Quần Jeans Slim Fit Xanh Đậm",
            "description": "Quần jeans nam form slim fit tôn dáng. Vải denim co giãn nhẹ, wash xanh đậm classic. Đường may kép chắc chắn, 5 túi tiện dụng.",
            "price": 550000, "original_price": 720000,
            "image_url": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=500",
            "category": "quan-nam", "tags": "jeans,slim fit,denim,xanh đậm,classic,co giãn",
            "gender": "nam", "material": "Denim Stretch", "style": "casual", "is_featured": True,
        },
        {
            "name": "Quần Kaki Chinos Kem",
            "description": "Quần kaki chinos nam màu kem, form regular fit thoải mái. Vải kaki cotton cao cấp, mềm mịn, không nhăn. Phù hợp đi làm và đi chơi.",
            "price": 420000, "original_price": 550000,
            "image_url": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=500",
            "category": "quan-nam", "tags": "kaki,chinos,kem,regular fit,cotton,công sở",
            "gender": "nam", "material": "Cotton Kaki", "style": "casual", "is_featured": False,
        },
        {
            "name": "Quần Short Thể Thao Đen",
            "description": "Quần short nam thể thao dryfit, nhanh khô, thoáng khí. Lưng thun co giãn kèm dây rút, túi khóa kéo hai bên. Lý tưởng cho gym và chạy bộ.",
            "price": 250000, "original_price": 350000,
            "image_url": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=500",
            "category": "quan-nam", "tags": "short,thể thao,dryfit,gym,chạy bộ,đen",
            "gender": "nam", "material": "Polyester Dryfit", "style": "sporty", "is_featured": False,
        },
        {
            "name": "Quần Jogger Streetwear Xám",
            "description": "Quần jogger nam phong cách streetwear, chất nỉ bông co giãn. Bo gấu cá tính, lưng thun thoải mái, hai túi sâu tiện lợi.",
            "price": 380000, "original_price": 480000,
            "image_url": "https://images.unsplash.com/photo-1552902865-b72c031ac5ea?w=500",
            "category": "quan-nam", "tags": "jogger,streetwear,nỉ bông,xám,bo gấu,trẻ trung",
            "gender": "nam", "material": "Cotton Fleece", "style": "streetwear", "is_featured": True,
        },
        {
            "name": "Quần Tây Âu Đen Slim",
            "description": "Quần tây âu nam đen form slim, vải polyester pha viscose chống nhăn. Ly ép sắc nét, phù hợp vest công sở và sự kiện trang trọng.",
            "price": 520000, "original_price": 680000,
            "image_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=500",
            "category": "quan-nam", "tags": "tây âu,đen,slim,công sở,chống nhăn,vest",
            "gender": "nam", "material": "Polyester Viscose", "style": "formal", "is_featured": False,
        },
        {
            "name": "Quần Jeans Rách Gối Xanh Nhạt",
            "description": "Quần jeans nam kiểu rách gối cá tính, wash xanh nhạt vintage. Denim dày dặn nhưng co giãn tốt, phong cách bụi bặm trẻ trung.",
            "price": 480000, "original_price": 620000,
            "image_url": "https://images.unsplash.com/photo-1604176354204-9268737828e4?w=500",
            "category": "quan-nam", "tags": "jeans,rách gối,vintage,xanh nhạt,cá tính,bụi bặm",
            "gender": "nam", "material": "Denim Stretch", "style": "streetwear", "is_featured": False,
        },
        {
            "name": "Quần Linen Ống Rộng Be",
            "description": "Quần linen nam ống rộng màu be, phong cách minimalist. Chất liệu linen tự nhiên mát mẻ cho mùa hè, lưng thun phía sau thoải mái.",
            "price": 450000, "original_price": None,
            "image_url": "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=500",
            "category": "quan-nam", "tags": "linen,ống rộng,be,minimalist,mát mẻ,mùa hè",
            "gender": "nam", "material": "Linen", "style": "casual", "is_featured": False,
        },

        # ==================== ÁO NỮ (8 sản phẩm) ====================
        {
            "name": "Áo Croptop Ribbed Trắng",
            "description": "Áo croptop nữ chất liệu ribbed cotton co giãn, form ôm tôn dáng. Cổ tròn basic, phối được với mọi loại quần và váy. Trendy và năng động.",
            "price": 180000, "original_price": 250000,
            "image_url": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=500",
            "category": "ao-nu", "tags": "croptop,ribbed,cotton,ôm,trắng,trendy,năng động",
            "gender": "nu", "material": "Ribbed Cotton", "style": "casual", "is_featured": True,
        },
        {
            "name": "Áo Sơ Mi Satin Hồng Pastel",
            "description": "Áo sơ mi nữ chất satin mềm mượt, màu hồng pastel ngọt ngào. Thiết kế cổ V thanh lịch, tay dài xắn được. Phù hợp đi làm và hẹn hò.",
            "price": 380000, "original_price": 480000,
            "image_url": "https://images.unsplash.com/photo-1551163943-3f6a855d1153?w=500",
            "category": "ao-nu", "tags": "sơ mi,satin,hồng pastel,cổ V,thanh lịch,công sở",
            "gender": "nu", "material": "Satin", "style": "formal", "is_featured": True,
        },
        {
            "name": "Áo Blouse Hoa Nhí Vintage",
            "description": "Áo blouse nữ họa tiết hoa nhí phong cách vintage romance. Chất voan mỏng nhẹ, cổ bèo xinh xắn, tay phồng nữ tính. Layer cùng áo lót bên trong.",
            "price": 320000, "original_price": 420000,
            "image_url": "https://images.unsplash.com/photo-1564257631407-4deb1f99d992?w=500",
            "category": "ao-nu", "tags": "blouse,hoa nhí,vintage,voan,cổ bèo,nữ tính",
            "gender": "nu", "material": "Chiffon", "style": "casual", "is_featured": False,
        },
        {
            "name": "Áo Len Cardigan Oversize Be",
            "description": "Áo len cardigan form oversize, chất len mềm mịn không xù. Cài nút phía trước, hai túi đắp hông. Ấm áp và thời thượng cho mùa thu đông.",
            "price": 520000, "original_price": 680000,
            "image_url": "https://images.unsplash.com/photo-1434389677669-e08b4cda3a0b?w=500",
            "category": "ao-nu", "tags": "cardigan,oversize,len,be,ấm áp,thu đông",
            "gender": "nu", "material": "Acrylic Wool", "style": "casual", "is_featured": True,
        },
        {
            "name": "Áo Thun Baby Tee Đen",
            "description": "Áo thun nữ baby tee form ôm vừa, tay ngắn cổ tròn. Chất cotton mềm mại, co giãn tốt. Phong cách Y2K đang hot trend, dễ mix & match.",
            "price": 160000, "original_price": 220000,
            "image_url": "https://images.unsplash.com/photo-1583846783214-7229a91b20ed?w=500",
            "category": "ao-nu", "tags": "baby tee,ôm,Y2K,cotton,đen,hot trend",
            "gender": "nu", "material": "Cotton Spandex", "style": "casual", "is_featured": False,
        },
        {
            "name": "Áo Khoác Denim Jacket Xanh Classic",
            "description": "Áo khoác denim jacket nữ kiểu classic, wash xanh truyền thống. Hai túi ngực nắp nút, đường may chắc chắn. Item must-have cho mọi tủ đồ.",
            "price": 580000, "original_price": 750000,
            "image_url": "https://images.unsplash.com/photo-1544642899-f0d6e5f6ed6f?w=500",
            "category": "ao-nu", "tags": "denim jacket,classic,xanh,must-have,bền bỉ,layering",
            "gender": "nu", "material": "Denim", "style": "casual", "is_featured": False,
        },
        {
            "name": "Áo Vest Blazer Nữ Trắng",
            "description": "Áo vest blazer nữ trắng kiểu dáng thời thượng. Vai vuông tạo form chuẩn, một nút cài sang trọng. Phù hợp phong cách power dressing công sở.",
            "price": 750000, "original_price": 950000,
            "image_url": "https://images.unsplash.com/photo-1632149877166-f75d49000351?w=500",
            "category": "ao-nu", "tags": "blazer,vest,trắng,power dressing,công sở,sang trọng",
            "gender": "nu", "material": "Polyester Blend", "style": "formal", "is_featured": False,
        },
        {
            "name": "Áo Off-Shoulder Ruffle Hồng",
            "description": "Áo off-shoulder nữ với chi tiết ruffle bèo nhún dọc ngực. Chất cotton pha nhẹ nhàng, tôn vai và xương quai xanh quyến rũ. Phù hợp đi biển và dạo phố.",
            "price": 290000, "original_price": 390000,
            "image_url": "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=500",
            "category": "ao-nu", "tags": "off-shoulder,ruffle,hồng,nữ tính,đi biển,quyến rũ",
            "gender": "nu", "material": "Cotton Blend", "style": "casual", "is_featured": False,
        },

        # ==================== VÁY & ĐẦM (7 sản phẩm) ====================
        {
            "name": "Đầm Midi Hoa Nhí Xanh Dương",
            "description": "Đầm midi nữ họa tiết hoa nhí trên nền xanh dương nhẹ nhàng. Chất voan 2 lớp, eo chun co giãn, chân váy xòe nhẹ bay bổng. Nữ tính và thanh lịch.",
            "price": 480000, "original_price": 620000,
            "image_url": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=500",
            "category": "vay-dam", "tags": "đầm midi,hoa nhí,xanh dương,voan,nữ tính,bay bổng",
            "gender": "nu", "material": "Chiffon", "style": "casual", "is_featured": True,
        },
        {
            "name": "Váy Mini A-line Đen",
            "description": "Váy mini nữ dáng A-line kinh điển, màu đen quyền lực. Vải tweed dày dặn, khóa kéo ẩn phía sau, lưng cao tôn chân dài. Phối được với mọi loại áo.",
            "price": 350000, "original_price": 450000,
            "image_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500",
            "category": "vay-dam", "tags": "váy mini,A-line,đen,tweed,quyền lực,classic",
            "gender": "nu", "material": "Tweed", "style": "formal", "is_featured": False,
        },
        {
            "name": "Đầm Maxi Boho Nâu Đất",
            "description": "Đầm maxi phong cách bohemian, hoạ tiết ethnic trên nền nâu đất. Chất liệu rayon mỏng nhẹ thoáng mát, thắt nơ eo. Hoàn hảo cho kỳ nghỉ biển.",
            "price": 550000, "original_price": 720000,
            "image_url": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=500",
            "category": "vay-dam", "tags": "maxi,boho,nâu đất,ethnic,rayon,đi biển",
            "gender": "nu", "material": "Rayon", "style": "casual", "is_featured": True,
        },
        {
            "name": "Đầm Công Sở Bút Chì Navy",
            "description": "Đầm bút chì nữ công sở, màu navy thanh lịch. Form ôm body tôn đường cong, tay ngắn, xẻ nhẹ phía sau dễ di chuyển. Vải dày dặn không nhăn.",
            "price": 620000, "original_price": 790000,
            "image_url": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500",
            "category": "vay-dam", "tags": "bút chì,công sở,navy,ôm body,thanh lịch,chuyên nghiệp",
            "gender": "nu", "material": "Polyester Spandex", "style": "formal", "is_featured": False,
        },
        {
            "name": "Đầm Dạ Hội Sequin Vàng Gold",
            "description": "Đầm dạ hội đính sequin vàng gold lấp lánh. Thiết kế hai dây gợi cảm, xẻ đùi cao, đuôi cá duyên dáng. Tỏa sáng tại mọi bữa tiệc và sự kiện.",
            "price": 1200000, "original_price": 1800000,
            "image_url": "https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=500",
            "category": "vay-dam", "tags": "dạ hội,sequin,vàng gold,hai dây,xẻ đùi,lấp lánh",
            "gender": "nu", "material": "Sequin Fabric", "style": "formal", "is_featured": True,
        },
        {
            "name": "Váy Jean Yếm Xanh Nhạt",
            "description": "Váy yếm jean nữ dáng chữ A, wash xanh nhạt trẻ trung. Hai quai điều chỉnh, túi phía trước, phối cùng áo thun hoặc áo sơ mi bên trong.",
            "price": 380000, "original_price": 480000,
            "image_url": "https://images.unsplash.com/photo-1562572159-4efc207f5aff?w=500",
            "category": "vay-dam", "tags": "váy yếm,jean,xanh nhạt,chữ A,trẻ trung,năng động",
            "gender": "nu", "material": "Denim", "style": "casual", "is_featured": False,
        },
        {
            "name": "Đầm Wrap Dress Đỏ Bordeaux",
            "description": "Đầm wrap dress nữ cổ chữ V, màu đỏ bordeaux quyến rũ. Thiết kế đắp chéo thắt nơ eo, tay dài nhẹ nhàng. Chất liệu rayon rũ đẹp tự nhiên.",
            "price": 490000, "original_price": 650000,
            "image_url": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=500",
            "category": "vay-dam", "tags": "wrap dress,đỏ bordeaux,cổ V,quyến rũ,thắt nơ,sang trọng",
            "gender": "nu", "material": "Rayon", "style": "formal", "is_featured": False,
        },

        # ==================== QUẦN NỮ (6 sản phẩm) ====================
        {
            "name": "Quần Jeans Ống Rộng Xanh Đậm",
            "description": "Quần jeans nữ ống rộng high-waist, wash xanh đậm. Chất denim dày dặn, co giãn nhẹ, tạo hiệu ứng chân dài miên man. Phong cách retro đang hot.",
            "price": 520000, "original_price": 680000,
            "image_url": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500",
            "category": "quan-nu", "tags": "jeans,ống rộng,high-waist,retro,xanh đậm,chân dài",
            "gender": "nu", "material": "Denim Stretch", "style": "casual", "is_featured": True,
        },
        {
            "name": "Quần Culottes Đen Thanh Lịch",
            "description": "Quần culottes nữ ống rộng 5 phân, màu đen sang trọng. Lưng cao kèm belt loop, vải polyester rũ đẹp. Phù hợp công sở lẫn dạo phố.",
            "price": 390000, "original_price": 520000,
            "image_url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=500",
            "category": "quan-nu", "tags": "culottes,đen,ống rộng,công sở,thanh lịch,sang trọng",
            "gender": "nu", "material": "Polyester", "style": "formal", "is_featured": False,
        },
        {
            "name": "Quần Legging Yoga Đen",
            "description": "Quần legging nữ chuyên dụng yoga và gym. Chất thun 4 chiều nén nhẹ tôn vòng 3, lưng cao nâng đỡ bụng. Thoáng khí, nhanh khô, không in dấu mồ hôi.",
            "price": 320000, "original_price": 420000,
            "image_url": "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=500",
            "category": "quan-nu", "tags": "legging,yoga,gym,thun 4 chiều,đen,tôn dáng",
            "gender": "nu", "material": "Nylon Spandex", "style": "sporty", "is_featured": False,
        },
        {
            "name": "Quần Short Linen Trắng",
            "description": "Quần short nữ chất linen mát mẻ cho mùa hè. Lưng thun co giãn thoải mái, đai nơ trang trí. Phối cùng áo crop top hoặc sơ mi rất xinh.",
            "price": 280000, "original_price": 380000,
            "image_url": "https://images.unsplash.com/photo-1551854838-212c50b4c184?w=500",
            "category": "quan-nu", "tags": "short,linen,trắng,mát mẻ,mùa hè,đai nơ",
            "gender": "nu", "material": "Linen", "style": "casual", "is_featured": False,
        },
        {
            "name": "Quần Palazzo Kẻ Sọc Nâu",
            "description": "Quần palazzo nữ ống suông rộng kẻ sọc nâu thanh lịch. Lưng cao tôn dáng, vải rũ mềm mại. Phong cách thanh lịch retro, phối cùng áo cổ lọ cực sang.",
            "price": 450000, "original_price": 590000,
            "image_url": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=500",
            "category": "quan-nu", "tags": "palazzo,kẻ sọc,nâu,retro,ống suông,thanh lịch",
            "gender": "nu", "material": "Polyester Blend", "style": "casual", "is_featured": False,
        },
        {
            "name": "Quần Cargo Túi Hộp Xanh Rêu",
            "description": "Quần cargo nữ nhiều túi hộp phong cách streetwear. Chất kaki dày dặn, lưng thun thoải mái, bo gấu cá tính. Màu xanh rêu military cool ngầu.",
            "price": 420000, "original_price": 550000,
            "image_url": "https://images.unsplash.com/photo-1584370848010-d7fe6bc767ec?w=500",
            "category": "quan-nu", "tags": "cargo,túi hộp,streetwear,xanh rêu,military,cool",
            "gender": "nu", "material": "Cotton Kaki", "style": "streetwear", "is_featured": True,
        },

        # ==================== PHỤ KIỆN (7 sản phẩm) ====================
        {
            "name": "Túi Tote Canvas Beige",
            "description": "Túi tote canvas size lớn, chất liệu canvas dày bền. Ngăn chính rộng rãi đựng laptop 14 inch, túi nhỏ bên trong. Phù hợp đi học, đi làm hàng ngày.",
            "price": 280000, "original_price": 350000,
            "image_url": "https://images.unsplash.com/photo-1544816155-12df9643f363?w=500",
            "category": "phu-kien", "tags": "túi tote,canvas,beige,đi học,đi làm,rộng rãi",
            "gender": "unisex", "material": "Canvas", "style": "casual", "is_featured": True,
        },
        {
            "name": "Kính Mát Aviator Gold",
            "description": "Kính mát unisex kiểu aviator gọng kim loại gold. Tròng kính chống UV400, phân cực giảm chói. Phong cách phi công classic, hợp mọi khuôn mặt.",
            "price": 350000, "original_price": 490000,
            "image_url": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=500",
            "category": "phu-kien", "tags": "kính mát,aviator,gold,chống UV,phi công,classic",
            "gender": "unisex", "material": "Kim loại", "style": "casual", "is_featured": False,
        },
        {
            "name": "Thắt Lưng Da Bò Đen",
            "description": "Thắt lưng nam da bò thật 100%, mặt khóa kim loại bạc sang trọng. Bản rộng 3.5cm phù hợp quần tây và jeans. Bền đẹp theo thời gian.",
            "price": 420000, "original_price": 580000,
            "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500",
            "category": "phu-kien", "tags": "thắt lưng,da bò,đen,khóa bạc,nam,sang trọng",
            "gender": "nam", "material": "Da bò thật", "style": "formal", "is_featured": False,
        },
        {
            "name": "Mũ Bucket Hat Đen",
            "description": "Mũ bucket hat unisex chất liệu cotton, phong cách đường phố. Vành rộng vừa che nắng tốt, có lỗ thông gió hai bên. Gấp gọn dễ mang theo.",
            "price": 150000, "original_price": 220000,
            "image_url": "https://images.unsplash.com/photo-1588850561407-ed78c334e67a?w=500",
            "category": "phu-kien", "tags": "bucket hat,mũ,đen,cotton,đường phố,che nắng",
            "gender": "unisex", "material": "Cotton", "style": "streetwear", "is_featured": False,
        },
        {
            "name": "Túi Đeo Chéo Mini Nữ Đen",
            "description": "Túi đeo chéo mini nữ da PU cao cấp. Thiết kế thời thượng với khóa xoay, dây đeo xích mảnh sang chảnh. Đựng vừa điện thoại, ví và son.",
            "price": 320000, "original_price": 420000,
            "image_url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=500",
            "category": "phu-kien", "tags": "túi đeo chéo,mini,đen,da PU,sang chảnh,nữ",
            "gender": "nu", "material": "Da PU", "style": "formal", "is_featured": True,
        },
        {
            "name": "Balo Laptop Minimal Đen",
            "description": "Balo laptop nam nữ phong cách minimal. Ngăn laptop riêng chống sốc 15.6 inch, ngăn phụ đựng bình nước. Vải Oxford chống nước, quai đeo êm vai.",
            "price": 480000, "original_price": 620000,
            "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500",
            "category": "phu-kien", "tags": "balo,laptop,minimal,đen,chống nước,unisex",
            "gender": "unisex", "material": "Oxford Fabric", "style": "casual", "is_featured": False,
        },
        {
            "name": "Khăn Quàng Cổ Cashmere Xám",
            "description": "Khăn quàng cổ unisex chất cashmere pha len mềm mượt. Kích thước 200x70cm đủ quấn nhiều kiểu. Giữ ấm cực tốt cho mùa đông, màu xám dễ phối đồ.",
            "price": 380000, "original_price": 520000,
            "image_url": "https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?w=500",
            "category": "phu-kien", "tags": "khăn quàng,cashmere,xám,giữ ấm,thu đông,unisex",
            "gender": "unisex", "material": "Cashmere Blend", "style": "casual", "is_featured": False,
        },

        # ==================== GIÀY DÉP (7 sản phẩm) ====================
        {
            "name": "Giày Sneaker Trắng Classic",
            "description": "Giày sneaker unisex full trắng phong cách minimalist. Đế cao su chống trượt, mũi giày rounded thoải mái. Item basic ai cũng cần có trong tủ giày.",
            "price": 650000, "original_price": 850000,
            "image_url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=500",
            "category": "giay-dep", "tags": "sneaker,trắng,minimalist,classic,cao su,basic",
            "gender": "unisex", "material": "Da tổng hợp", "style": "casual", "is_featured": True,
        },
        {
            "name": "Giày Cao Gót Mũi Nhọn Đen 7cm",
            "description": "Giày cao gót nữ mũi nhọn thanh lịch, gót nhọn 7cm vừa phải. Da bóng premium, đệm êm bên trong. Tôn dáng sang trọng cho mọi bộ outfit công sở.",
            "price": 550000, "original_price": 720000,
            "image_url": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500",
            "category": "giay-dep", "tags": "cao gót,mũi nhọn,đen,7cm,da bóng,sang trọng",
            "gender": "nu", "material": "Da tổng hợp", "style": "formal", "is_featured": True,
        },
        {
            "name": "Sandal Quai Ngang Nữ Kem",
            "description": "Sandal nữ quai ngang đế bệt, màu kem nhẹ nhàng. Quai da mềm không cắt chân, đế đệm cloudfoam êm ái. Nhẹ nhàng thoải mái cho mùa hè.",
            "price": 290000, "original_price": 380000,
            "image_url": "https://images.unsplash.com/photo-1603487742131-4160ec999306?w=500",
            "category": "giay-dep", "tags": "sandal,quai ngang,kem,đế bệt,mùa hè,thoải mái",
            "gender": "nu", "material": "Da PU", "style": "casual", "is_featured": False,
        },
        {
            "name": "Giày Boots Chelsea Đen Nam",
            "description": "Giày boots Chelsea nam da bò thật, cổ chun co giãn dễ mang. Đế cao su dày chống trượt, mũi tròn classic. Phong cách lịch lãm mà vẫn cá tính.",
            "price": 890000, "original_price": 1200000,
            "image_url": "https://images.unsplash.com/photo-1638247025967-b4e38f787b76?w=500",
            "category": "giay-dep", "tags": "boots,chelsea,đen,da bò,lịch lãm,cá tính",
            "gender": "nam", "material": "Da bò thật", "style": "formal", "is_featured": False,
        },
        {
            "name": "Giày Thể Thao Running Xám",
            "description": "Giày thể thao nam chuyên chạy bộ với công nghệ đệm khí. Upper mesh thoáng khí, đế Phylon siêu nhẹ. Hỗ trợ vòm chân, chống sốc hiệu quả.",
            "price": 750000, "original_price": 980000,
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500",
            "category": "giay-dep", "tags": "thể thao,running,xám,đệm khí,mesh,siêu nhẹ",
            "gender": "nam", "material": "Mesh + Phylon", "style": "sporty", "is_featured": True,
        },
        {
            "name": "Dép Slides Unisex Đen",
            "description": "Dép slides unisex đế dày cloud cushion êm ái. Quai rộng logo nổi, chống trượt trên nền ướt. Mang trong nhà, đi pool party hay chạy ra ngoài đều hợp.",
            "price": 180000, "original_price": 250000,
            "image_url": "https://images.unsplash.com/photo-1603487742131-4160ec999306?w=500",
            "category": "giay-dep", "tags": "slides,dép,đen,cloud cushion,chống trượt,đa năng",
            "gender": "unisex", "material": "EVA Foam", "style": "casual", "is_featured": False,
        },
        {
            "name": "Giày Loafer Da Nam Nâu",
            "description": "Giày loafer nam da bò, kiểu penny loafer truyền thống. Không dây tiện lợi, đế da chống trượt. Phù hợp mang với quần tây, chinos hoặc quần short cho ngày hè.",
            "price": 680000, "original_price": 880000,
            "image_url": "https://images.unsplash.com/photo-1614252369475-531eba835eb1?w=500",
            "category": "giay-dep", "tags": "loafer,da bò,nâu,penny loafer,lịch lãm,tiện lợi",
            "gender": "nam", "material": "Da bò thật", "style": "formal", "is_featured": False,
        },
    ]

    for p_data in products_data:
        cat_slug = p_data.pop("category")
        p_data["category_id"] = cat_map[cat_slug].id
        product = Product(**p_data)
        db.session.add(product)

    db.session.commit()
    print(f"[OK] Đã tạo {len(products_data)} products.")
    return Product.query.all()


def seed_users():
    """Tạo 5 user mẫu để test + 1 admin account"""
    users_data = [
        {"username": "admin", "email": "admin@luxe.vn", "password": "admin123", "full_name": "Admin LUXE", "is_admin": True},
        {"username": "minh_anh", "email": "minhanh@example.com", "password": "password123", "full_name": "Nguyễn Minh Anh"},
        {"username": "duc_huy", "email": "duchuy@example.com", "password": "password123", "full_name": "Trần Đức Huy"},
        {"username": "thu_trang", "email": "thutrang@example.com", "password": "password123", "full_name": "Lê Thu Trang"},
        {"username": "hoang_nam", "email": "hoangnam@example.com", "password": "password123", "full_name": "Phạm Hoàng Nam"},
        {"username": "my_linh", "email": "mylinh@example.com", "password": "password123", "full_name": "Vũ Mỹ Linh"},
    ]

    created_users = []
    for u_data in users_data:
        user = User(
            username=u_data["username"],
            email=u_data["email"],
            password_hash=generate_password_hash(u_data["password"]),
            full_name=u_data["full_name"],
            is_admin=u_data.get("is_admin", False),
        )
        db.session.add(user)
        created_users.append(user)

    db.session.commit()
    print(f"[OK] Đã tạo {len(users_data)} users.")
    print(f"     Admin account: username=admin / password=admin123")
    print(f"     User accounts: password mặc định = password123")
    return User.query.all()


def seed_interactions(users, products):
    """
    Tạo lịch sử tương tác giả lập cho recommendation system.
    Mỗi user sẽ có sở thích khác nhau để test collaborative filtering.
    """
    random.seed(42)

    # Định nghĩa sở thích cho từng user
    # User 1 (minh_anh - nữ): Thích thời trang nữ, váy đầm, phụ kiện
    # User 2 (duc_huy - nam): Thích streetwear nam, giày sneaker
    # User 3 (thu_trang - nữ): Thích formal, công sở
    # User 4 (hoang_nam - nam): Thích sporty, casual nam
    # User 5 (my_linh - nữ): Thích casual nữ, bohemian

    user_preferences = {
        1: {"genders": ["nu", "unisex"], "styles": ["casual", "formal"], "categories": ["ao-nu", "vay-dam", "phu-kien"]},
        2: {"genders": ["nam", "unisex"], "styles": ["streetwear", "casual"], "categories": ["ao-nam", "quan-nam", "giay-dep"]},
        3: {"genders": ["nu", "unisex"], "styles": ["formal"], "categories": ["ao-nu", "vay-dam", "giay-dep"]},
        4: {"genders": ["nam", "unisex"], "styles": ["sporty", "casual"], "categories": ["ao-nam", "quan-nam", "giay-dep"]},
        5: {"genders": ["nu", "unisex"], "styles": ["casual"], "categories": ["ao-nu", "vay-dam", "quan-nu", "phu-kien"]},
    }

    # Tạo map category slug
    from models import Category
    cat_map = {c.slug: c.id for c in Category.query.all()}

    interaction_count = 0

    for user in users:
        prefs = user_preferences.get(user.id, user_preferences[1])

        # Tìm các sản phẩm phù hợp với sở thích
        preferred_products = [
            p for p in products
            if p.gender in prefs["genders"] or p.style in prefs["styles"]
        ]

        other_products = [p for p in products if p not in preferred_products]

        # User xem nhiều sản phẩm ưa thích (view)
        viewed_preferred = random.sample(preferred_products, min(12, len(preferred_products)))
        for product in viewed_preferred:
            interaction = UserInteraction(
                user_id=user.id,
                product_id=product.id,
                interaction_type="view",
                rating=round(random.uniform(3.5, 5.0), 1),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            )
            db.session.add(interaction)
            interaction_count += 1

        # User cũng xem một số sản phẩm khác (ít hơn)
        viewed_others = random.sample(other_products, min(4, len(other_products)))
        for product in viewed_others:
            interaction = UserInteraction(
                user_id=user.id,
                product_id=product.id,
                interaction_type="view",
                rating=round(random.uniform(1.0, 3.5), 1),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            )
            db.session.add(interaction)
            interaction_count += 1

        # User thêm vào giỏ hàng một số sản phẩm ưa thích
        carted = random.sample(viewed_preferred, min(5, len(viewed_preferred)))
        for product in carted:
            interaction = UserInteraction(
                user_id=user.id,
                product_id=product.id,
                interaction_type="cart",
                rating=round(random.uniform(4.0, 5.0), 1),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 20)),
            )
            db.session.add(interaction)
            interaction_count += 1

        # User mua 2-4 sản phẩm
        purchased = random.sample(carted, min(random.randint(2, 4), len(carted)))
        for product in purchased:
            interaction = UserInteraction(
                user_id=user.id,
                product_id=product.id,
                interaction_type="purchase",
                rating=round(random.uniform(4.0, 5.0), 1),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 15)),
            )
            db.session.add(interaction)
            interaction_count += 1

    db.session.commit()
    print(f"[OK] Đã tạo {interaction_count} user interactions.")


def seed_orders(users, products):
    """Tạo một số đơn hàng mẫu"""
    random.seed(42)
    order_count = 0

    addresses = [
        "123 Nguyễn Huệ, Quận 1, TP.HCM",
        "456 Lê Lợi, Quận 3, TP.HCM",
        "789 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội",
        "321 Bạch Đằng, Hải Châu, Đà Nẵng",
        "654 Nguyễn Văn Linh, Quận 7, TP.HCM",
    ]

    phones = ["0901234567", "0912345678", "0923456789", "0934567890", "0945678901"]

    # Lọc bỏ admin, chỉ tạo đơn hàng cho user thường
    normal_users = [u for u in users if not u.is_admin]

    for i, user in enumerate(normal_users):
        # Mỗi user có 1-2 đơn hàng
        num_orders = random.randint(1, 2)
        user_products = random.sample(products, min(num_orders * 3, len(products)))

        for j in range(num_orders):
            order_products = user_products[j * 2:(j + 1) * 2 + 1]
            if not order_products:
                continue

            total = sum(p.price * random.randint(1, 2) for p in order_products)

            order = Order(
                user_id=user.id,
                total_amount=total,
                status=random.choice(["confirmed", "shipped", "delivered"]),
                full_name=user.full_name,
                phone=phones[i % len(phones)],
                address=addresses[i % len(addresses)],
                note="Giao giờ hành chính" if random.random() > 0.5 else "",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
            )
            db.session.add(order)
            db.session.flush()  # Để lấy order.id

            for product in order_products:
                qty = random.randint(1, 2)
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    price=product.price,
                )
                db.session.add(order_item)

            order_count += 1

    db.session.commit()
    print(f"[OK] Đã tạo {order_count} orders.")


def run_seed():
    """Chạy toàn bộ quá trình seed data"""
    app = create_app()

    with app.app_context():
        # Xóa database cũ và tạo lại
        db.drop_all()
        db.create_all()
        print("=" * 50)
        print("  SEED DATA - Fashion E-commerce Store")
        print("=" * 50)

        # Bước 1: Tạo categories
        categories = seed_categories()

        # Bước 2: Tạo products
        products = seed_products(categories)

        # Bước 3: Tạo users
        users = seed_users()

        # Bước 4: Tạo interactions (cho recommendation system)
        seed_interactions(users, products)

        # Bước 5: Tạo orders
        seed_orders(users, products)

        print("=" * 50)
        print("  SEED HOÀN TẤT!")
        print(f"  - {Category.query.count()} categories")
        print(f"  - {Product.query.count()} products")
        print(f"  - {User.query.count()} users")
        print(f"  - {UserInteraction.query.count()} interactions")
        print(f"  - {Order.query.count()} orders")
        print("=" * 50)


if __name__ == "__main__":
    run_seed()
