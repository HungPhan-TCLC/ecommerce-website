-- =============================================================================
-- seed_static.sql
-- Static seed data cho Fashion E-commerce Store (PostgreSQL)
-- Chứa: categories, products, users (base + eval)
--
-- Password hashes được pre-generate bằng Werkzeug scrypt (chạy _gen_user_sql.py):
--   admin/admin123 | user thường/password123 | eval user/evalpass123
--
-- Chạy độc lập (sau khi đã CREATE TABLE):
--   psql -U postgres -d luxe_fashion -f seed_static.sql
-- Hoặc được gọi tự động từ seed_data.py / setup_and_seed.py.
-- =============================================================================

-- ─── CATEGORIES ──────────────────────────────────────────────────────────────
INSERT INTO categories (name, slug, description) VALUES
    ('Áo nam',    'ao-nam',    'Áo thun, áo sơ mi, áo khoác nam'),
    ('Quần nam',  'quan-nam',  'Quần jeans, quần kaki, quần short nam'),
    ('Áo nữ',     'ao-nu',     'Áo kiểu, áo croptop, áo sơ mi nữ'),
    ('Váy & Đầm', 'vay-dam',   'Váy ngắn, đầm dạ hội, đầm công sở'),
    ('Quần nữ',   'quan-nu',   'Quần jeans, quần ống rộng, quần legging'),
    ('Phụ kiện',  'phu-kien',  'Túi xách, mắt kính, thắt lưng, mũ'),
    ('Giày dép',  'giay-dep',  'Giày sneaker, giày cao gót, sandal')
ON CONFLICT (slug) DO NOTHING;


-- ─── PRODUCTS ─────────────────────────────────────────────────────────────────
-- category_id tham chiếu theo thứ tự INSERT ở trên:
--   1 = ao-nam | 2 = quan-nam | 3 = ao-nu | 4 = vay-dam
--   5 = quan-nu | 6 = phu-kien | 7 = giay-dep

INSERT INTO products (name, description, price, original_price, image_url, category_id, tags, gender, material, style, is_featured, stock) VALUES

-- ==================== ÁO NAM (8 sản phẩm) ====================
(
    'Áo Thun Cotton Basic Trắng',
    'Áo thun nam cổ tròn chất liệu cotton 100% mềm mại, thoáng mát. Thiết kế basic dễ phối đồ, phù hợp mặc hàng ngày hoặc layer bên trong áo khoác.',
    199000, 299000,
    'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nam'),
    'basic,cotton,thoáng mát,cổ tròn,trắng,mùa hè',
    'nam', 'Cotton 100%', 'casual', TRUE, 50
),
(
    'Áo Sơ Mi Oxford Slim Fit',
    'Áo sơ mi nam vải Oxford cao cấp, form Slim Fit tôn dáng. Cổ button-down lịch lãm, phù hợp đi làm và dự tiệc. Chống nhăn tốt.',
    450000, 590000,
    'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nam'),
    'sơ mi,oxford,slim fit,công sở,lịch lãm,chống nhăn',
    'nam', 'Oxford Cotton', 'formal', TRUE, 50
),
(
    'Áo Polo Pique Classic',
    'Áo polo nam chất liệu vải pique dệt kim thoáng khí. Logo thêu tinh tế trên ngực trái, cổ bẻ sang trọng. Phù hợp đi chơi golf hoặc dạo phố.',
    350000, 450000,
    'https://images.unsplash.com/photo-1586790170083-2f9ceadc732d?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nam'),
    'polo,pique,cổ bẻ,thanh lịch,thể thao,golf',
    'nam', 'Cotton Pique', 'casual', FALSE, 50
),
(
    'Áo Khoác Bomber Jacket Đen',
    'Áo khoác bomber jacket phong cách streetwear. Chất liệu polyester chống gió nhẹ, lớp lót mềm mại. Bo gấu và tay áo co giãn, khóa kéo YKK bền bỉ.',
    650000, 850000,
    'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nam'),
    'bomber,jacket,streetwear,chống gió,đen,thu đông',
    'nam', 'Polyester', 'streetwear', TRUE, 50
),
(
    'Áo Hoodie Oversize Xám',
    'Áo hoodie nam form oversize trẻ trung. Chất nỉ bông dày dặn, mũ trùm rộng, túi kangaroo phía trước. Giữ ấm tốt cho mùa đông.',
    420000, 550000,
    'https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nam'),
    'hoodie,oversize,nỉ bông,giữ ấm,xám,thu đông',
    'nam', 'Cotton Fleece', 'streetwear', FALSE, 50
),
(
    'Áo Thun Graphic Art Print',
    'Áo thun nam in hình nghệ thuật độc đáo. Cotton co giãn 4 chiều, bền màu sau nhiều lần giặt. Form regular fit thoải mái.',
    280000, 380000,
    'https://images.unsplash.com/photo-1503341504253-dff4f94032ef?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nam'),
    'thun,graphic,nghệ thuật,cotton,in hình,trẻ trung',
    'nam', 'Cotton Spandex', 'casual', FALSE, 50
),
(
    'Áo Blazer Linen Xanh Navy',
    'Áo blazer nam chất liệu linen mát mẻ, phong cách smart casual. Hai nút cài, hai túi hông nắp, túi ngực. Phù hợp mặc đi làm hoặc dự sự kiện.',
    890000, 1200000,
    'https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nam'),
    'blazer,linen,smart casual,navy,công sở,sự kiện',
    'nam', 'Linen', 'formal', TRUE, 50
),
(
    'Áo Thun Henley Tay Dài',
    'Áo thun henley nam tay dài, cổ mở 3 nút tạo điểm nhấn nam tính. Vải cotton pha spandex co giãn, thoải mái vận động.',
    320000, NULL,
    'https://images.unsplash.com/photo-1618517351616-38fb9c5210c6?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nam'),
    'henley,tay dài,cotton,nam tính,basic,thu đông',
    'nam', 'Cotton Spandex', 'casual', FALSE, 50
),

-- ==================== QUẦN NAM (7 sản phẩm) ====================
(
    'Quần Jeans Slim Fit Xanh Đậm',
    'Quần jeans nam form slim fit tôn dáng. Vải denim co giãn nhẹ, wash xanh đậm classic. Đường may kép chắc chắn, 5 túi tiện dụng.',
    550000, 720000,
    'https://images.unsplash.com/photo-1542272604-787c3835535d?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nam'),
    'jeans,slim fit,denim,xanh đậm,classic,co giãn',
    'nam', 'Denim Stretch', 'casual', TRUE, 50
),
(
    'Quần Kaki Chinos Kem',
    'Quần kaki chinos nam màu kem, form regular fit thoải mái. Vải kaki cotton cao cấp, mềm mịn, không nhăn. Phù hợp đi làm và đi chơi.',
    420000, 550000,
    'https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nam'),
    'kaki,chinos,kem,regular fit,cotton,công sở',
    'nam', 'Cotton Kaki', 'casual', FALSE, 50
),
(
    'Quần Short Thể Thao Đen',
    'Quần short nam thể thao dryfit, nhanh khô, thoáng khí. Lưng thun co giãn kèm dây rút, túi khóa kéo hai bên. Lý tưởng cho gym và chạy bộ.',
    250000, 350000,
    'https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nam'),
    'short,thể thao,dryfit,gym,chạy bộ,đen',
    'nam', 'Polyester Dryfit', 'sporty', FALSE, 50
),
(
    'Quần Jogger Streetwear Xám',
    'Quần jogger nam phong cách streetwear, chất nỉ bông co giãn. Bo gấu cá tính, lưng thun thoải mái, hai túi sâu tiện lợi.',
    380000, 480000,
    'https://images.unsplash.com/photo-1552902865-b72c031ac5ea?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nam'),
    'jogger,streetwear,nỉ bông,xám,bo gấu,trẻ trung',
    'nam', 'Cotton Fleece', 'streetwear', TRUE, 50
),
(
    'Quần Tây Âu Đen Slim',
    'Quần tây âu nam đen form slim, vải polyester pha viscose chống nhăn. Ly ép sắc nét, phù hợp vest công sở và sự kiện trang trọng.',
    520000, 680000,
    'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nam'),
    'tây âu,đen,slim,công sở,chống nhăn,vest',
    'nam', 'Polyester Viscose', 'formal', FALSE, 50
),
(
    'Quần Jeans Rách Gối Xanh Nhạt',
    'Quần jeans nam kiểu rách gối cá tính, wash xanh nhạt vintage. Denim dày dặn nhưng co giãn tốt, phong cách bụi bặm trẻ trung.',
    480000, 620000,
    'https://images.unsplash.com/photo-1604176354204-9268737828e4?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nam'),
    'jeans,rách gối,vintage,xanh nhạt,cá tính,bụi bặm',
    'nam', 'Denim Stretch', 'streetwear', FALSE, 50
),
(
    'Quần Linen Ống Rộng Be',
    'Quần linen nam ống rộng màu be, phong cách minimalist. Chất liệu linen tự nhiên mát mẻ cho mùa hè, lưng thun phía sau thoải mái.',
    450000, NULL,
    'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nam'),
    'linen,ống rộng,be,minimalist,mát mẻ,mùa hè',
    'nam', 'Linen', 'casual', FALSE, 50
),

-- ==================== ÁO NỮ (8 sản phẩm) ====================
(
    'Áo Croptop Ribbed Trắng',
    'Áo croptop nữ chất liệu ribbed cotton co giãn, form ôm tôn dáng. Cổ tròn basic, phối được với mọi loại quần và váy. Trendy và năng động.',
    180000, 250000,
    'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nu'),
    'croptop,ribbed,cotton,ôm,trắng,trendy,năng động',
    'nu', 'Ribbed Cotton', 'casual', TRUE, 50
),
(
    'Áo Sơ Mi Satin Hồng Pastel',
    'Áo sơ mi nữ chất satin mềm mượt, màu hồng pastel ngọt ngào. Thiết kế cổ V thanh lịch, tay dài xắn được. Phù hợp đi làm và hẹn hò.',
    380000, 480000,
    'https://images.unsplash.com/photo-1551163943-3f6a855d1153?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nu'),
    'sơ mi,satin,hồng pastel,cổ V,thanh lịch,công sở',
    'nu', 'Satin', 'formal', TRUE, 50
),
(
    'Áo Blouse Hoa Nhí Vintage',
    'Áo blouse nữ họa tiết hoa nhí phong cách vintage romance. Chất voan mỏng nhẹ, cổ bèo xinh xắn, tay phồng nữ tính. Layer cùng áo lót bên trong.',
    320000, 420000,
    'https://images.unsplash.com/photo-1564257631407-4deb1f99d992?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nu'),
    'blouse,hoa nhí,vintage,voan,cổ bèo,nữ tính',
    'nu', 'Chiffon', 'casual', FALSE, 50
),
(
    'Áo Len Cardigan Oversize Be',
    'Áo len cardigan form oversize, chất len mềm mịn không xù. Cài nút phía trước, hai túi đắp hông. Ấm áp và thời thượng cho mùa thu đông.',
    520000, 680000,
    'https://images.unsplash.com/photo-1434389677669-e08b4cda3a0b?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nu'),
    'cardigan,oversize,len,be,ấm áp,thu đông',
    'nu', 'Acrylic Wool', 'casual', TRUE, 50
),
(
    'Áo Thun Baby Tee Đen',
    'Áo thun nữ baby tee form ôm vừa, tay ngắn cổ tròn. Chất cotton mềm mại, co giãn tốt. Phong cách Y2K đang hot trend, dễ mix & match.',
    160000, 220000,
    'https://images.unsplash.com/photo-1583846783214-7229a91b20ed?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nu'),
    'baby tee,ôm,Y2K,cotton,đen,hot trend',
    'nu', 'Cotton Spandex', 'casual', FALSE, 50
),
(
    'Áo Khoác Denim Jacket Xanh Classic',
    'Áo khoác denim jacket nữ kiểu classic, wash xanh truyền thống. Hai túi ngực nắp nút, đường may chắc chắn. Item must-have cho mọi tủ đồ.',
    580000, 750000,
    'https://images.unsplash.com/photo-1544642899-f0d6e5f6ed6f?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nu'),
    'denim jacket,classic,xanh,must-have,bền bỉ,layering',
    'nu', 'Denim', 'casual', FALSE, 50
),
(
    'Áo Vest Blazer Nữ Trắng',
    'Áo vest blazer nữ trắng kiểu dáng thời thượng. Vai vuông tạo form chuẩn, một nút cài sang trọng. Phù hợp phong cách power dressing công sở.',
    750000, 950000,
    'https://images.unsplash.com/photo-1632149877166-f75d49000351?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nu'),
    'blazer,vest,trắng,power dressing,công sở,sang trọng',
    'nu', 'Polyester Blend', 'formal', FALSE, 50
),
(
    'Áo Off-Shoulder Ruffle Hồng',
    'Áo off-shoulder nữ với chi tiết ruffle bèo nhún dọc ngực. Chất cotton pha nhẹ nhàng, tôn vai và xương quai xanh quyến rũ. Phù hợp đi biển và dạo phố.',
    290000, 390000,
    'https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=500',
    (SELECT id FROM categories WHERE slug = 'ao-nu'),
    'off-shoulder,ruffle,hồng,nữ tính,đi biển,quyến rũ',
    'nu', 'Cotton Blend', 'casual', FALSE, 50
),

-- ==================== VÁY & ĐẦM (7 sản phẩm) ====================
(
    'Đầm Midi Hoa Nhí Xanh Dương',
    'Đầm midi nữ họa tiết hoa nhí trên nền xanh dương nhẹ nhàng. Chất voan 2 lớp, eo chun co giãn, chân váy xòe nhẹ bay bổng. Nữ tính và thanh lịch.',
    480000, 620000,
    'https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=500',
    (SELECT id FROM categories WHERE slug = 'vay-dam'),
    'đầm midi,hoa nhí,xanh dương,voan,nữ tính,bay bổng',
    'nu', 'Chiffon', 'casual', TRUE, 50
),
(
    'Váy Mini A-line Đen',
    'Váy mini nữ dáng A-line kinh điển, màu đen quyền lực. Vải tweed dày dặn, khóa kéo ẩn phía sau, lưng cao tôn chân dài. Phối được với mọi loại áo.',
    350000, 450000,
    'https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500',
    (SELECT id FROM categories WHERE slug = 'vay-dam'),
    'váy mini,A-line,đen,tweed,quyền lực,classic',
    'nu', 'Tweed', 'formal', FALSE, 50
),
(
    'Đầm Maxi Boho Nâu Đất',
    'Đầm maxi phong cách bohemian, hoạ tiết ethnic trên nền nâu đất. Chất liệu rayon mỏng nhẹ thoáng mát, thắt nơ eo. Hoàn hảo cho kỳ nghỉ biển.',
    550000, 720000,
    'https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=500',
    (SELECT id FROM categories WHERE slug = 'vay-dam'),
    'maxi,boho,nâu đất,ethnic,rayon,đi biển',
    'nu', 'Rayon', 'casual', TRUE, 50
),
(
    'Đầm Công Sở Bút Chì Navy',
    'Đầm bút chì nữ công sở, màu navy thanh lịch. Form ôm body tôn đường cong, tay ngắn, xẻ nhẹ phía sau dễ di chuyển. Vải dày dặn không nhăn.',
    620000, 790000,
    'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500',
    (SELECT id FROM categories WHERE slug = 'vay-dam'),
    'bút chì,công sở,navy,ôm body,thanh lịch,chuyên nghiệp',
    'nu', 'Polyester Spandex', 'formal', FALSE, 50
),
(
    'Đầm Dạ Hội Sequin Vàng Gold',
    'Đầm dạ hội đính sequin vàng gold lấp lánh. Thiết kế hai dây gợi cảm, xẻ đùi cao, đuôi cá duyên dáng. Tỏa sáng tại mọi bữa tiệc và sự kiện.',
    1200000, 1800000,
    'https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=500',
    (SELECT id FROM categories WHERE slug = 'vay-dam'),
    'dạ hội,sequin,vàng gold,hai dây,xẻ đùi,lấp lánh',
    'nu', 'Sequin Fabric', 'formal', TRUE, 50
),
(
    'Váy Jean Yếm Xanh Nhạt',
    'Váy yếm jean nữ dáng chữ A, wash xanh nhạt trẻ trung. Hai quai điều chỉnh, túi phía trước, phối cùng áo thun hoặc áo sơ mi bên trong.',
    380000, 480000,
    'https://images.unsplash.com/photo-1562572159-4efc207f5aff?w=500',
    (SELECT id FROM categories WHERE slug = 'vay-dam'),
    'váy yếm,jean,xanh nhạt,chữ A,trẻ trung,năng động',
    'nu', 'Denim', 'casual', FALSE, 50
),
(
    'Đầm Wrap Dress Đỏ Bordeaux',
    'Đầm wrap dress nữ cổ chữ V, màu đỏ bordeaux quyến rũ. Thiết kế đắp chéo thắt nơ eo, tay dài nhẹ nhàng. Chất liệu rayon rũ đẹp tự nhiên.',
    490000, 650000,
    'https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=500',
    (SELECT id FROM categories WHERE slug = 'vay-dam'),
    'wrap dress,đỏ bordeaux,cổ V,quyến rũ,thắt nơ,sang trọng',
    'nu', 'Rayon', 'formal', FALSE, 50
),

-- ==================== QUẦN NỮ (6 sản phẩm) ====================
(
    'Quần Jeans Ống Rộng Xanh Đậm',
    'Quần jeans nữ ống rộng high-waist, wash xanh đậm. Chất denim dày dặn, co giãn nhẹ, tạo hiệu ứng chân dài miên man. Phong cách retro đang hot.',
    520000, 680000,
    'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nu'),
    'jeans,ống rộng,high-waist,retro,xanh đậm,chân dài',
    'nu', 'Denim Stretch', 'casual', TRUE, 50
),
(
    'Quần Culottes Đen Thanh Lịch',
    'Quần culottes nữ ống rộng 5 phân, màu đen sang trọng. Lưng cao kèm belt loop, vải polyester rũ đẹp. Phù hợp công sở lẫn dạo phố.',
    390000, 520000,
    'https://images.unsplash.com/photo-1509631179647-0177331693ae?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nu'),
    'culottes,đen,ống rộng,công sở,thanh lịch,sang trọng',
    'nu', 'Polyester', 'formal', FALSE, 50
),
(
    'Quần Legging Yoga Đen',
    'Quần legging nữ chuyên dụng yoga và gym. Chất thun 4 chiều nén nhẹ tôn vòng 3, lưng cao nâng đỡ bụng. Thoáng khí, nhanh khô, không in dấu mồ hôi.',
    320000, 420000,
    'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nu'),
    'legging,yoga,gym,thun 4 chiều,đen,tôn dáng',
    'nu', 'Nylon Spandex', 'sporty', FALSE, 50
),
(
    'Quần Short Linen Trắng',
    'Quần short nữ chất linen mát mẻ cho mùa hè. Lưng thun co giãn thoải mái, đai nơ trang trí. Phối cùng áo crop top hoặc sơ mi rất xinh.',
    280000, 380000,
    'https://images.unsplash.com/photo-1551854838-212c50b4c184?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nu'),
    'short,linen,trắng,mát mẻ,mùa hè,đai nơ',
    'nu', 'Linen', 'casual', FALSE, 50
),
(
    'Quần Palazzo Kẻ Sọc Nâu',
    'Quần palazzo nữ ống suông rộng kẻ sọc nâu thanh lịch. Lưng cao tôn dáng, vải rũ mềm mại. Phong cách thanh lịch retro, phối cùng áo cổ lọ cực sang.',
    450000, 590000,
    'https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nu'),
    'palazzo,kẻ sọc,nâu,retro,ống suông,thanh lịch',
    'nu', 'Polyester Blend', 'casual', FALSE, 50
),
(
    'Quần Cargo Túi Hộp Xanh Rêu',
    'Quần cargo nữ nhiều túi hộp phong cách streetwear. Chất kaki dày dặn, lưng thun thoải mái, bo gấu cá tính. Màu xanh rêu military cool ngầu.',
    420000, 550000,
    'https://images.unsplash.com/photo-1584370848010-d7fe6bc767ec?w=500',
    (SELECT id FROM categories WHERE slug = 'quan-nu'),
    'cargo,túi hộp,streetwear,xanh rêu,military,cool',
    'nu', 'Cotton Kaki', 'streetwear', TRUE, 50
),

-- ==================== PHỤ KIỆN (7 sản phẩm) ====================
(
    'Túi Tote Canvas Beige',
    'Túi tote canvas size lớn, chất liệu canvas dày bền. Ngăn chính rộng rãi đựng laptop 14 inch, túi nhỏ bên trong. Phù hợp đi học, đi làm hàng ngày.',
    280000, 350000,
    'https://images.unsplash.com/photo-1544816155-12df9643f363?w=500',
    (SELECT id FROM categories WHERE slug = 'phu-kien'),
    'túi tote,canvas,beige,đi học,đi làm,rộng rãi',
    'unisex', 'Canvas', 'casual', TRUE, 50
),
(
    'Kính Mát Aviator Gold',
    'Kính mát unisex kiểu aviator gọng kim loại gold. Tròng kính chống UV400, phân cực giảm chói. Phong cách phi công classic, hợp mọi khuôn mặt.',
    350000, 490000,
    'https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=500',
    (SELECT id FROM categories WHERE slug = 'phu-kien'),
    'kính mát,aviator,gold,chống UV,phi công,classic',
    'unisex', 'Kim loại', 'casual', FALSE, 50
),
(
    'Thắt Lưng Da Bò Đen',
    'Thắt lưng nam da bò thật 100%, mặt khóa kim loại bạc sang trọng. Bản rộng 3.5cm phù hợp quần tây và jeans. Bền đẹp theo thời gian.',
    420000, 580000,
    'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500',
    (SELECT id FROM categories WHERE slug = 'phu-kien'),
    'thắt lưng,da bò,đen,khóa bạc,nam,sang trọng',
    'nam', 'Da bò thật', 'formal', FALSE, 50
),
(
    'Mũ Bucket Hat Đen',
    'Mũ bucket hat unisex chất liệu cotton, phong cách đường phố. Vành rộng vừa che nắng tốt, có lỗ thông gió hai bên. Gấp gọn dễ mang theo.',
    150000, 220000,
    'https://images.unsplash.com/photo-1588850561407-ed78c334e67a?w=500',
    (SELECT id FROM categories WHERE slug = 'phu-kien'),
    'bucket hat,mũ,đen,cotton,đường phố,che nắng',
    'unisex', 'Cotton', 'streetwear', FALSE, 50
),
(
    'Túi Đeo Chéo Mini Nữ Đen',
    'Túi đeo chéo mini nữ da PU cao cấp. Thiết kế thời thượng với khóa xoay, dây đeo xích mảnh sang chảnh. Đựng vừa điện thoại, ví và son.',
    320000, 420000,
    'https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=500',
    (SELECT id FROM categories WHERE slug = 'phu-kien'),
    'túi đeo chéo,mini,đen,da PU,sang chảnh,nữ',
    'nu', 'Da PU', 'formal', TRUE, 50
),
(
    'Balo Laptop Minimal Đen',
    'Balo laptop nam nữ phong cách minimal. Ngăn laptop riêng chống sốc 15.6 inch, ngăn phụ đựng bình nước. Vải Oxford chống nước, quai đeo êm vai.',
    480000, 620000,
    'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500',
    (SELECT id FROM categories WHERE slug = 'phu-kien'),
    'balo,laptop,minimal,đen,chống nước,unisex',
    'unisex', 'Oxford Fabric', 'casual', FALSE, 50
),
(
    'Khăn Quàng Cổ Cashmere Xám',
    'Khăn quàng cổ unisex chất cashmere pha len mềm mượt. Kích thước 200x70cm đủ quấn nhiều kiểu. Giữ ấm cực tốt cho mùa đông, màu xám dễ phối đồ.',
    380000, 520000,
    'https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?w=500',
    (SELECT id FROM categories WHERE slug = 'phu-kien'),
    'khăn quàng,cashmere,xám,giữ ấm,thu đông,unisex',
    'unisex', 'Cashmere Blend', 'casual', FALSE, 50
),

-- ==================== GIÀY DÉP (7 sản phẩm) ====================
(
    'Giày Sneaker Trắng Classic',
    'Giày sneaker unisex full trắng phong cách minimalist. Đế cao su chống trượt, mũi giày rounded thoải mái. Item basic ai cũng cần có trong tủ giày.',
    650000, 850000,
    'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=500',
    (SELECT id FROM categories WHERE slug = 'giay-dep'),
    'sneaker,trắng,minimalist,classic,cao su,basic',
    'unisex', 'Da tổng hợp', 'casual', TRUE, 50
),
(
    'Giày Cao Gót Mũi Nhọn Đen 7cm',
    'Giày cao gót nữ mũi nhọn thanh lịch, gót nhọn 7cm vừa phải. Da bóng premium, đệm êm bên trong. Tôn dáng sang trọng cho mọi bộ outfit công sở.',
    550000, 720000,
    'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500',
    (SELECT id FROM categories WHERE slug = 'giay-dep'),
    'cao gót,mũi nhọn,đen,7cm,da bóng,sang trọng',
    'nu', 'Da tổng hợp', 'formal', TRUE, 50
),
(
    'Sandal Quai Ngang Nữ Kem',
    'Sandal nữ quai ngang đế bệt, màu kem nhẹ nhàng. Quai da mềm không cắt chân, đế đệm cloudfoam êm ái. Nhẹ nhàng thoải mái cho mùa hè.',
    290000, 380000,
    'https://images.unsplash.com/photo-1603487742131-4160ec999306?w=500',
    (SELECT id FROM categories WHERE slug = 'giay-dep'),
    'sandal,quai ngang,kem,đế bệt,mùa hè,thoải mái',
    'nu', 'Da PU', 'casual', FALSE, 50
),
(
    'Giày Boots Chelsea Đen Nam',
    'Giày boots Chelsea nam da bò thật, cổ chun co giãn dễ mang. Đế cao su dày chống trượt, mũi tròn classic. Phong cách lịch lãm mà vẫn cá tính.',
    890000, 1200000,
    'https://images.unsplash.com/photo-1638247025967-b4e38f787b76?w=500',
    (SELECT id FROM categories WHERE slug = 'giay-dep'),
    'boots,chelsea,đen,da bò,lịch lãm,cá tính',
    'nam', 'Da bò thật', 'formal', FALSE, 50
),
(
    'Giày Thể Thao Running Xám',
    'Giày thể thao nam chuyên chạy bộ với công nghệ đệm khí. Upper mesh thoáng khí, đế Phylon siêu nhẹ. Hỗ trợ vòm chân, chống sốc hiệu quả.',
    750000, 980000,
    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500',
    (SELECT id FROM categories WHERE slug = 'giay-dep'),
    'thể thao,running,xám,đệm khí,mesh,siêu nhẹ',
    'nam', 'Mesh + Phylon', 'sporty', TRUE, 50
),
(
    'Dép Slides Unisex Đen',
    'Dép slides unisex đế dày cloud cushion êm ái. Quai rộng logo nổi, chống trượt trên nền ướt. Mang trong nhà, đi pool party hay chạy ra ngoài đều hợp.',
    180000, 250000,
    'https://images.unsplash.com/photo-1603487742131-4160ec999306?w=500',
    (SELECT id FROM categories WHERE slug = 'giay-dep'),
    'slides,dép,đen,cloud cushion,chống trượt,đa năng',
    'unisex', 'EVA Foam', 'casual', FALSE, 50
),
(
    'Giày Loafer Da Nam Nâu',
    'Giày loafer nam da bò, kiểu penny loafer truyền thống. Không dây tiện lợi, đế da chống trượt. Phù hợp mang với quần tây, chinos hoặc quần short cho ngày hè.',
    680000, 880000,
    'https://images.unsplash.com/photo-1614252369475-531eba835eb1?w=500',
    (SELECT id FROM categories WHERE slug = 'giay-dep'),
    'loafer,da bò,nâu,penny loafer,lịch lãm,tiện lợi',
    'nam', 'Da bò thật', 'formal', FALSE, 50
)

ON CONFLICT (name) DO NOTHING;


-- ─── BASE USERS ─────────────────────────────────────────────────────────────
-- 1 admin + 5 user mẫu | passwords: admin=admin123, others=password123
INSERT INTO users (username, email, password_hash, full_name, is_admin) VALUES
    ('admin', 'admin@luxe.vn', 'scrypt:32768:8:1$gdZN5ztVG9wX7qIE$babcc2117cfbaceb6eb31af4801764a103a57e612cdc3c4d6bce1c80ee1ada18aebc16ee167aadd2ce5a83f7dec93c3208f6d1a0a23d8911d5f5a7aad458785f', 'Admin LUXE', TRUE),
    ('minh_anh', 'minhanh@example.com', 'scrypt:32768:8:1$piiffj18qhsabXlI$c3a844bea2ec489257a05d41a2d39655f374a533c770c6002c24f7167c72ca89be2b745d4c3b885b1df8abb6f8b9fe1b79ca24b996a3eb29a5f60d7ae4cb3c0b', 'Nguyễn Minh Anh', FALSE),
    ('duc_huy', 'duchuy@example.com', 'scrypt:32768:8:1$BOSCxBbTYd2cRX8h$503517e4b0c64b17ab1a49a078c5c632342e990ec4186a3e58f3f587fb765f38b10e49a4f67c1a10ad77d58fa94c7e34ffdf369de21398321402938fe50fed4b', 'Trần Đức Huy', FALSE),
    ('thu_trang', 'thutrang@example.com', 'scrypt:32768:8:1$y1zoq7e4xTuhiEBL$e9d56e450382fd63c6fb01d59b526c532809190df668208f9de177835b1fc568e67de79985ca3e0f181cd4077b79a63903a532361e088b49ef8e60ed6a7579e1', 'Lê Thu Trang', FALSE),
    ('hoang_nam', 'hoangnam@example.com', 'scrypt:32768:8:1$VT42RHCDIINwjKgh$37e239ae500728d51d90cc03d101e050fbfb266e35f34b7588238567abfec630354959f022ba425e57b368d4df6c43f6a722006e71fbdfa92dd5e3a85426dcc7', 'Phạm Hoàng Nam', FALSE),
    ('my_linh', 'mylinh@example.com', 'scrypt:32768:8:1$oqEYk4JlcTi6UIUe$b853f37947a067b7aa0d0a905a5688697f57458b26790bc3e55f47e6f5c19380324b3d7fcdd67d5dc6de519e658814248b02a701ad2ef2c78c8fd628170b1279', 'Vũ Mỹ Linh', FALSE)
ON CONFLICT (username) DO NOTHING;


-- ─── EVAL USERS (15 users cho evaluation metrics) ───────────────────────────
-- password: evalpass123
INSERT INTO users (username, email, password_hash, full_name, is_admin) VALUES
    ('linh_trang', 'linhtrang@eval.vn', 'scrypt:32768:8:1$8mvUX2l8kqQ11nev$df7496e77ed23407c697d1beb08932095b65d8ae2c7fd7df83c0093a56efc0be80cd4b074ef7ca362d7de1d49607ab46fdbbf36e1bd48ddf5f73c3dcd681ddc7', 'Đinh Linh Trang', FALSE),
    ('an_khang', 'ankhang@eval.vn', 'scrypt:32768:8:1$DFvvWd1QeKkFWMTh$3f042249e378d2ede4d6bc925d0cecff27c1f707264ad3130bf62578d9c39819d144ee79db76dbc58ffd3ab4af2961f3cd6fede14f30638e881f323a2515434b', 'Bùi An Khang', FALSE),
    ('phuong_anh', 'phuonganh@eval.vn', 'scrypt:32768:8:1$qmgeU1rMVY4RCw7J$b6d52ec70a4f7c842f1f19175c9417eed96bbbdd412fe6b6573398dd982651743cc66f5ef729e51d0f78745338761347262c3bd4cf9c6610730cc3d046e35a51', 'Cao Phương Anh', FALSE),
    ('tuan_kiet', 'tuankiet@eval.vn', 'scrypt:32768:8:1$smudBsSH6Ab4ENUm$81a9a45270ad47752feecc24200200bfcab798c6194bb88f765f7e3442df163455b2d74b90b04899ea2b7729c727ec16f5a8c9859243eba5053f899037f9caa6', 'Ngô Tuấn Kiệt', FALSE),
    ('thu_ha', 'thuha@eval.vn', 'scrypt:32768:8:1$a9K7kzTlB5iQ0TRK$34dffa546126d358156a81293f6ca70d3a38f0daa13d0d361e70cde3c24b247a2c0149b89bff9dc2350f43dbfef26021af95550a4929e3bb321c9a7f4c028918', 'Đặng Thu Hà', FALSE),
    ('minh_chau', 'minhchau@eval.vn', 'scrypt:32768:8:1$nGUuXhNeWceuBh7C$73fd5f28689f5272d352db303203c2003c8fa0dbff863366a6943d85831df171817ec39da2d5b50faac1cd18dac8ceaddb3a4ee53fb78321f1d03c291bf0fea0', 'Trịnh Minh Châu', FALSE),
    ('hai_dang', 'haidang@eval.vn', 'scrypt:32768:8:1$whBb3oXPAsr5XYEz$daefab221a540d2ed64e45e1b21c7485f90591351abb02b326a6ff31d3571eef0c2ec52d0d30869ab3fd123f89d2ec4508bc3feed08c0554c0032a183ae66e81', 'Lý Hải Đăng', FALSE),
    ('bao_anh', 'baoanhev@eval.vn', 'scrypt:32768:8:1$EWM8w06Wou5Qm6TD$5a7686e7df74bf8f40f8243b5798c17dd18803b4c558a94ef38786f19bee2158af8fefbbcedb7327a0a967e2afdff6c3b058b161c37bf3ed83710756f6c6cf2d', 'Nguyễn Bảo Anh', FALSE),
    ('viet_hung', 'viethung@eval.vn', 'scrypt:32768:8:1$T3IbJiQ0HT6dOeXo$273f029726a698d20a4170eb155ad99af69d376b4e4d12218d2efb5c7c3e11664428a6fff539a760afa6a61fe873208ee64b26502d72b8ad1cbad8a084e4c91a', 'Phạm Việt Hùng', FALSE),
    ('khanh_linh', 'khanhlinh@eval.vn', 'scrypt:32768:8:1$jASNaYFEjwOYqvA2$b57ec68588775aa2d951cfeefa759f916799ee9bb261df9f10a097032d090e42f011574e8508ed1b1ed9b1a6bf54ce804b2e378733dcd272ebeec87cb96bef88', 'Hồ Khánh Linh', FALSE),
    ('duc_minh', 'ducminh@eval.vn', 'scrypt:32768:8:1$6pqdKGduCUzgMCwz$c8bb80e31e90c46bc829599fa9c920e627c63545024bf600f8c28e5c127392107a3467ed3b5db29ce70e0ebdf3c43601289730109febf412f1108d99335c3f7a', 'Tô Đức Minh', FALSE),
    ('thanh_van', 'thanhvan@eval.vn', 'scrypt:32768:8:1$lk7K4wQ2sNbfZFNu$a17a29ad000e8bd3def7960556fce86903b51e0042f5a2d3cd33f00437cb0139155415d1f4deba2cda91ebdd87a2904b7dc04bd12955b226fac6bc0af3588ae2', 'Lê Thanh Vân', FALSE),
    ('quoc_bao', 'quocbao@eval.vn', 'scrypt:32768:8:1$sqQbeqJI0ZQSlVkb$b05e88014827b0c227b464e895e262446df4a6b5613afd7f3d6c566dfb38607c7316d27132da326b41ab7a966bc8571fd1b8c6c5ec23f15489ad29d8b24dbbb8', 'Mai Quốc Bảo', FALSE),
    ('ngoc_han', 'ngochan@eval.vn', 'scrypt:32768:8:1$xKrQLu4aLRXs4HJ6$e4b4395ee63b1d1cbf5071c07aa69aff7997dc8f3eeed58c720c71bf0b158ee568a6737d5bf9a2cd52ab2ff6a47a1b30afadbdacd5f687bf0e70e71ce65478a1', 'Dương Ngọc Hân', FALSE),
    ('bach_khoa', 'bachkhoa@eval.vn', 'scrypt:32768:8:1$Gu2Gqc2PM1ToMsSb$7fc3342e99699ca27b5b9543ffb7a185d245a59721e08be664594761f4db2efbf198afe0a3b1ebc4cf9fb174545745311a0ef1ceeeb38e652fbd322354ff1671', 'Võ Bách Khoa', FALSE)
ON CONFLICT (username) DO NOTHING;
