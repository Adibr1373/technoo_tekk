import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import uuid
import re

# تنظیم logging
logging.basicConfig(
    filename='bot_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# توکن ربات
TOKEN = '8460902591:AAGyiiyW7uJkc-Ey3yRKlZcuy6W4-bpMuMw'
bot = telebot.TeleBot(TOKEN)

# آیدی کانال و گروه
CHANNEL_ID = '-1002723263803'  # @technoo_tek
GROUP_ID = '-1003084729118'   # @technoo_tekK
OWNER_ID = 239716777  # آیدی ادمین

# ذخیره موقت اطلاعات کاربر
user_data = {}
# ذخیره محصولات
products = {}
next_product_number = 1111

# دسته‌بندی‌ها
CATEGORIES = {
    "1": {
        "name": "لوازم جانبی موبایل",
        "sub": {
            "1.1": "محافظت و شخصی‌سازی",
            "1.2": "اتصال و انرژی",
            "1.3": "کارایی و سرگرمی"
        },
        "guide": "محافظت و شخصی‌سازی (قاب و کاور، محافظ صفحه نمایش، گارد لنز دوربین، کیف، بند و حلقه نگهدارنده، هولدر)\nاتصال و انرژی (شارژر دیواری و خودرویی، شارژر بی‌سیم، کابل شارژ، پاوربانک، فلش مموری OTG، کارت حافظه MicroSD، آداپتورها)\nکارایی و سرگرمی (هدفون و هندزفری، اسپیکر بلوتوث و وایرلس، رینگ لایت و LED، هولدر و پایه نگهدارنده، کنترلر و گیم‌پد موبایل، خنک‌کننده و فن)"
    },
    "2": {
        "name": "گجت‌های سلامتی",
        "sub": {
            "2.1": "نظارت بر سلامت و پوشیدنی‌ها",
            "2.2": "مراقبت شخصی و محیطی"
        },
        "guide": "نظارت بر سلامت و پوشیدنی‌ها (ساعت هوشمند، دستبند فیتنس)\nمراقبت شخصی و محیطی (دستگاه بخور و مرطوب‌کننده هوا، هدست‌های مدیتیشن، ردیاب خواب)"
    }
}

SUBCATEGORY_CODES = {
    "محافظت و شخصی‌سازی": "PS",
    "اتصال و انرژی": "CE",
    "کارایی و سرگرمی": "PE",
    "نظارت بر سلامت و پوشیدنی‌ها": "HW",
    "مراقبت شخصی و محیطی": "PC"
}

# تابع برای تصفیه متن برای Markdown
def sanitize_markdown(text):
    if not text:
        return "جدید و باکیفیت!"
    # جایگزینی کاراکترهای مشکل‌ساز برای Markdown
    text = re.sub(r'([*_`\[\\])', r'\\\1', text)
    # حذف یا جایگزینی کاراکترهای غیرچاپی یا خاص
    text = re.sub(r'[^\w\s\d.,!?()@#\-]', '', text)
    # اطمینان از اینکه متن خالی نیست
    return text.strip() or "جدید و باکیفیت!"

# منوهای inline
def main_menu(user_id):
    markup = InlineKeyboardMarkup()
    if user_id == OWNER_ID:
        markup.add(InlineKeyboardButton("مدیریت", callback_data="admin_panel"))
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("انتشار جدید", callback_data="new_post"))
    return markup

def new_post_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("محصول جدید", callback_data="new_product"))
    markup.add(InlineKeyboardButton("بازگشت", callback_data="back_main"))
    return markup

def category_menu():
    markup = InlineKeyboardMarkup()
    for cat_id, cat in CATEGORIES.items():
        for sub_id, sub_name in cat["sub"].items():
            markup.add(InlineKeyboardButton(f"{cat['name']} - {sub_name}", callback_data=f"cat_{cat_id}_{sub_id}"))
    markup.add(InlineKeyboardButton("بازگشت", callback_data="back_to_new_post"))
    return markup

def back_button(step, cat_id=None, sub_id=None):
    markup = InlineKeyboardMarkup()
    if step == "category":
        markup.add(InlineKeyboardButton("بازگشت", callback_data="back_to_new_post"))
    elif step == "title_price":
        markup.add(InlineKeyboardButton("بازگشت", callback_data=f"back_to_category_{cat_id}_{sub_id}"))
    elif step == "desc_image":
        markup.add(InlineKeyboardButton("رد شدن (Skip)", callback_data="skip_desc_image"))
        markup.add(InlineKeyboardButton("بازگشت", callback_data=f"back_to_title_price_{cat_id}_{sub_id}"))
    elif step == "stock":
        markup.add(InlineKeyboardButton("بازگشت", callback_data=f"back_to_desc_image_{cat_id}_{sub_id}"))
    return markup

def preview_menu(product_id):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("تأیید و انتشار", callback_data="confirm_preview"),
        InlineKeyboardButton("ویرایش", callback_data="edit_preview")
    )
    markup.add(InlineKeyboardButton("اضافه به سبد خرید", callback_data=f"add_to_cart_{product_id}"))
    return markup

def target_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("کانال تکنو تک", callback_data="post_channel"),
        InlineKeyboardButton("گروه تکنو تک", callback_data="post_group")
    )
    markup.add(InlineKeyboardButton("هر دو", callback_data="post_both"))
    return markup

# تولید شناسه محصول
def generate_product_id(subcategory):
    global next_product_number
    code = SUBCATEGORY_CODES.get(subcategory, "XX")
    product_id = f"{code}{next_product_number}"
    if product_id not in products:
        next_product_number += 1
        return product_id
    next_product_number += 1
    return generate_product_id(subcategory)

# فرمت پست محصول
def generate_post(user_id):
    data = user_data.get(user_id, {})
    title = sanitize_markdown(data.get('title', 'نامعلوم'))
    description = sanitize_markdown(data.get('description', 'جدید و باکیفیت!'))
    post_text = f"""
🎉 **تکنو تک تقدیم می‌کند: {title}**  
💡 *ویژگی‌ها:* {description}  
💰 *قیمت:* {data.get('price', '0')} تومان  
📦 *موجودی:* {data.get('stock', '0')} عدد  
🆔 *شناسه:* {data.get('product_id', 'در حال تولید')}  
🔗 *سفارش فوری:* @TechnoTakBot  
#تکنوتک #خرید_آنلاین
"""
    return post_text

# ذخیره محصول
def save_product(user_id):
    data = user_data[user_id]
    product_id = generate_product_id(data['subcategory'])
    products[product_id] = {
        'title': data['title'],
        'description': data.get('description', 'جدید و باکیفیت!'),
        'price': data['price'],
        'image': data.get('image'),
        'category': data['category'],
        'subcategory': data['subcategory'],
        'stock': data.get('stock', 0)
    }
    logger.info(f"محصول ذخیره شد: {product_id}, {data['title']}")
    return product_id

# ارسال پست
def publish_post(user_id):
    data = user_data.get(user_id, {})
    target = data.get('target')
    targets = []
    if target == 'channel':
        targets.append(CHANNEL_ID)
    elif target == 'group':
        targets.append(GROUP_ID)
    elif target == 'both':
        targets.extend([CHANNEL_ID, GROUP_ID])
    
    post_text = generate_post(user_id)
    product_id = data['product_id']
    try:
        for target_id in targets:
            if data.get('image'):
                bot.send_photo(target_id, data['image'], caption=post_text, parse_mode='Markdown', reply_markup=preview_menu(product_id))
            else:
                bot.send_message(target_id, post_text, parse_mode='Markdown', reply_markup=preview_menu(product_id))
        logger.info(f"پست منتشر شد به {targets} توسط کاربر {user_id}")
        return "پست با موفقیت منتشر شد! 🚀"
    except Exception as e:
        logger.error(f"خطا در انتشار: {str(e)}")
        return f"خطا: {str(e)}"

# هندلر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    logger.info(f"دستور /start از کاربر {user_id}")
    bot.send_message(user_id, "سلام! به تکنو تک خوش اومدید 😊", reply_markup=main_menu(user_id))

# هندلر پیام‌های متنی و غیره برای جلوگیری از ورودی‌های ناخواسته
@bot.message_handler(content_types=['text', 'photo'])
def handle_unexpected_input(message):
    user_id = message.chat.id
    valid_steps = ['title_price', 'desc_image', 'stock']
    if user_id not in user_data or user_data[user_id].get('step') not in valid_steps:
        bot.send_message(user_id, "لطفاً از منوی مدیریت شروع کنید!", reply_markup=main_menu(user_id))
        logger.warning(f"ورودی غیرمنتظره از کاربر {user_id}: {message.text if message.text else 'غیر متنی'}")
        return

# هندلر کال‌بک‌ها
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    if user_id != OWNER_ID:
        bot.answer_callback_query(call.id, "فقط ادمین‌ها دسترسی دارن!")
        return
    logger.info(f"کال‌بک دریافت شد: {call.data} از کاربر {user_id}")

    if call.data == "admin_panel":
        bot.edit_message_text("به بخش مدیریت خوش اومدید!", call.message.chat.id, call.message.message_id, reply_markup=admin_menu())
    elif call.data == "new_post":
        bot.edit_message_text("چی منتشر کنیم؟", call.message.chat.id, call.message.message_id, reply_markup=new_post_menu())
    elif call.data == "new_product":
        user_data[user_id] = {'step': 'category'}
        bot.edit_message_text("دسته‌بندی محصول چیه؟ (گام ۱/۳)", call.message.chat.id, call.message.message_id, reply_markup=category_menu())
    elif call.data.startswith("cat_"):
        cat_id, sub_id = call.data.split("_")[1:]
        user_data[user_id] = {
            'step': 'title_price',
            'category': CATEGORIES[cat_id]['name'],
            'subcategory': CATEGORIES[cat_id]['sub'][sub_id],
            'cat_id': cat_id,
            'sub_id': sub_id
        }
        bot.edit_message_text("نام و قیمت رو باهم وارد کن (مثال: قاب گوشی | 200,000): (گام ۲/۳)", call.message.chat.id, call.message.message_id, reply_markup=back_button("title_price", cat_id, sub_id))
        bot.register_next_step_handler(call.message, get_title_price)
    elif call.data == "skip_desc_image":
        user_data[user_id]['description'] = "جدید و باکیفیت!"
        user_data[user_id]['image'] = None
        user_data[user_id]['step'] = 'stock'
        bot.edit_message_text("موجودی (تعداد):", call.message.chat.id, call.message.message_id, reply_markup=back_button("stock", user_data[user_id]['cat_id'], user_data[user_id]['sub_id']))
        bot.register_next_step_handler(call.message, get_stock)
    elif call.data == "confirm_preview":
        user_data[user_id]['step'] = 'target'
        bot.edit_message_text("کجا منتشر بشه؟", call.message.chat.id, call.message.message_id, reply_markup=target_menu())
    elif call.data in ["post_channel", "post_group", "post_both"]:
        user_data[user_id]['target'] = call.data[5:]
        save_product(user_id)
        result = publish_post(user_id)
        bot.edit_message_text(result, call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))
        bot.clear_step_handler_by_chat_id(user_id)
        del user_data[user_id]
    elif call.data == "edit_preview":
        user_data[user_id]['step'] = 'title_price'
        bot.edit_message_text("نام و قیمت رو باهم وارد کن (مثال: قاب گوشی | 200,000): (گام ۲/۳)", call.message.chat.id, call.message.message_id, reply_markup=back_button("title_price", user_data[user_id]['cat_id'], user_data[user_id]['sub_id']))
        bot.register_next_step_handler(call.message, get_title_price)
    elif call.data.startswith("back_to_category_"):
        cat_id, sub_id = call.data.split("_")[3:]
        user_data[user_id] = {'step': 'category'}
        bot.edit_message_text("دسته‌بندی محصول چیه؟ (گام ۱/۳)", call.message.chat.id, call.message.message_id, reply_markup=category_menu())
    elif call.data.startswith("back_to_title_price_"):
        cat_id, sub_id = call.data.split("_")[3:]
        user_data[user_id]['step'] = 'title_price'
        bot.edit_message_text("نام و قیمت رو باهم وارد کن (مثال: قاب گوشی | 200,000): (گام ۲/۳)", call.message.chat.id, call.message.message_id, reply_markup=back_button("title_price", cat_id, sub_id))
        bot.register_next_step_handler(call.message, get_title_price)
    elif call.data.startswith("back_to_desc_image_"):
        cat_id, sub_id = call.data.split("_")[3:]
        user_data[user_id]['step'] = 'desc_image'
        bot.edit_message_text("توضیحات یا عکس می‌خوای؟ (گام ۳/۳)", call.message.chat.id, call.message.message_id, reply_markup=back_button("desc_image", cat_id, sub_id))
        bot.register_next_step_handler(call.message, get_desc_image)
    elif call.data == "back_main":
        bot.edit_message_text("سلام! به تکنو تک خوش اومدید 😊", call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))
        if user_id in user_data:
            del user_data[user_id]
    bot.answer_callback_query(call.id)

# گرفتن عنوان و قیمت
def get_title_price(message):
    user_id = message.chat.id
    if user_id not in user_data or user_data[user_id].get('step') != 'title_price':
        bot.send_message(user_id, "لطفاً از منوی مدیریت شروع کنید!", reply_markup=main_menu(user_id))
        return
    try:
        title, price = message.text.split("|")
        price = int(price.replace(",", "").strip())
        if price <= 0:
            raise ValueError
        user_data[user_id]['title'] = title.strip()
        user_data[user_id]['price'] = f"{price:,}"
        user_data[user_id]['step'] = 'desc_image'
        bot.send_message(user_id, "توضیحات یا عکس می‌خوای؟ (گام ۳/۳)", reply_markup=back_button("desc_image", user_data[user_id]['cat_id'], user_data[user_id]['sub_id']))
        logger.info(f"عنوان و قیمت دریافت شد: {title.strip()}, {price} برای کاربر {user_id}")
        bot.register_next_step_handler(message, get_desc_image)
    except ValueError:
        logger.warning(f"ورودی نام و قیمت نامعتبر از کاربر {user_id}: {message.text}")
        bot.send_message(user_id, "لطفاً به فرمت 'نام | قیمت' وارد کنید (مثال: قاب گوشی | 200,000)", reply_markup=back_button("title_price", user_data[user_id]['cat_id'], user_data[user_id]['sub_id']))
        bot.register_next_step_handler(message, get_title_price)

# گرفتن توضیحات یا تصویر
def get_desc_image(message):
    user_id = message.chat.id
    if user_id not in user_data or user_data[user_id].get('step') != 'desc_image':
        bot.send_message(user_id, "لطفاً از منوی مدیریت شروع کنید!", reply_markup=main_menu(user_id))
        return
    if message.photo:
        user_data[user_id]['image'] = message.photo[-1].file_id
        user_data[user_id]['description'] = "جدید و باکیفیت!"
        user_data[user_id]['step'] = 'stock'
        bot.send_message(user_id, "موجودی (تعداد):", reply_markup=back_button("stock", user_data[user_id]['cat_id'], user_data[user_id]['sub_id']))
        logger.info(f"تصویر محصول دریافت شد برای کاربر {user_id}")
        bot.register_next_step_handler(message, get_stock)
    elif message.text:
        user_data[user_id]['description'] = message.text[:200]
        user_data[user_id]['image'] = None
        user_data[user_id]['step'] = 'stock'
        bot.send_message(user_id, "موجودی (تعداد):", reply_markup=back_button("stock", user_data[user_id]['cat_id'], user_data[user_id]['sub_id']))
        logger.info(f"توضیحات محصول دریافت شد: {message.text[:50]}... برای کاربر {user_id}")
        bot.register_next_step_handler(message, get_stock)
    else:
        logger.warning(f"ورودی نامعتبر از کاربر {user_id}")
        bot.send_message(user_id, "لطفاً توضیحات (حداکثر 200 کاراکتر) یا یه عکس آپلود کنید:", reply_markup=back_button("desc_image", user_data[user_id]['cat_id'], user_data[user_id]['sub_id']))
        bot.register_next_step_handler(message, get_desc_image)

# گرفتن موجودی
def get_stock(message):
    user_id = message.chat.id
    if user_id not in user_data or user_data[user_id].get('step') != 'stock':
        bot.send_message(user_id, "لطفاً از منوی مدیریت شروع کنید!", reply_markup=main_menu(user_id))
        return
    try:
        stock = int(message.text)
        if stock < 0:
            bot.send_message(user_id, "موجودی نمی‌تونه منفی باشه! 😊", reply_markup=back_button("stock", user_data[user_id]['cat_id'], user_data[user_id]['sub_id']))
            bot.register_next_step_handler(message, get_stock)
            return
        user_data[user_id]['stock'] = stock
        user_data[user_id]['product_id'] = generate_product_id(user_data[user_id]['subcategory'])
        user_data[user_id]['step'] = 'preview'
        bot.send_message(user_id, f"پیش‌نمایش محصول:\n{generate_post(user_id)}", reply_markup=preview_menu(user_data[user_id]['product_id']), parse_mode='Markdown')
        logger.info(f"موجودی محصول دریافت شد: {stock} برای کاربر {user_id}")
        bot.clear_step_handler_by_chat_id(user_id)
    except ValueError:
        logger.warning(f"ورودی موجودی نامعتبر از کاربر {user_id}: {message.text}")
        bot.send_message(user_id, "لطفاً فقط عدد وارد کنید! 😊", reply_markup=back_button("stock", user_data[user_id]['cat_id'], user_data[user_id]['sub_id']))
        bot.register_next_step_handler(message, get_stock)

# شروع ربات
logger.info("ربات شروع شد")
bot.polling()
