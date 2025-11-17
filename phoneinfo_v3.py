import os
import time
import requests
import phonenumbers
from phonenumbers import geocoder, carrier, timezone, NumberParseException, PhoneNumberType
from telebot import TeleBot, types
from telebot.types import LabeledPrice, PreCheckoutQuery
from datetime import datetime, timedelta
import subprocess
import sys
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
PROVIDER_TOKEN = os.getenv('PROVIDER_TOKEN')

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

bot = TeleBot(TOKEN)


user_languages = {}


messages = {
    'tr': {
        'welcome_select': "Lütfen botu kullanmak için bir dil seçin:",
        'welcome': "👋 Merhaba! Telefon Sorgu Botu'na hoş geldiniz!\n\n"
                   "Bu bot ile telefon numaralarına ait bazı bilgileri öğrenebilirsiniz. Bilgi almak için lütfen bir telefon numarası gönderin.\n\n"
                   "📋 Özellikler:\n"
                   "    ├📞 Telefon numarası bilgilerini sorgulama\n"
                   "    ├🔒 Gizli bilgilere premium erişim\n"
                   "    └📍 Canlı konum izleme (premium üyelik gerektirir)\n\n"
                   "Başlamak için bir telefon numarası gönderin veya aşağıdaki 'Yardım' butonuna tıklayın.",
        'help': "📖 <b>Yardım Menüsü</b>\n\nBu bot ile çeşitli telefon numarası bilgilerini öğrenebilirsiniz.\n\n🔹 <b>Nasıl Kullanılır:</b>\n    └ Bir telefon numarası gönderin, bot size numara ile ilgili bilgileri iletsin.\n\n🔹 <b>Komutlar:</b>\n    ├ /start - Karşılama mesajını gösterir\n    ├ /help - Bu yardım mesajını gösterir\n    └ Telefon numarası - Bilgi sorgulama\n\n📲 Örnek kullanım:\n<i>+905555555555</i> gibi bir numara göndererek sorgulama yapabilirsiniz.",
        'settings': "⚙️ <b>Ayarlar</b>: Dil Seçenekleri",
        'settings_button': "⚙️ Ayarlar",
        'help_button': "ℹ️ Yardım",
        'premium_button': "💎 Premium Satın Al",
        'back_button': "🔙 Geri",
        'invalid_number': "❗ Geçersiz telefon numarası formatı. Lütfen geçerli bir telefon numarası gönderin. örnek: +905055555555",
        'phone_info': "📞 <b>Telefon Numarası Bilgileri:</b>",
        'country': "Ülke",
        'operator': "Operatör",
        'timezones': "Saat Dilimleri",
        'number_type': "Numara Türü",
        'valid_number': "Numara Geçerliliği",
        'national_number': "Ulusal Numara",
        'area_code': "Bölge Kodu",
        'e164_format': "E164 formatı",
        'person_info': "👤 <b>Kişi Bilgileri (Gizli):</b>",
        'live_location_warning': "⚠️ <b>Canlı Konum İzleme ve Tüm Kişi Bilgileri</b>: Bu bilgilere erişmek için premium üyelik gereklidir.\nPremium erişim almak için destek ekibimize ulaşın.",
        'premium_required': "Premium gerektirir",
        'location_button': "📍Konumu Gör📍",
        'premium_warning': "Premium üye değilsiniz. Bu özelliği kullanmak için premium üye olun.",
        'purchase_title': "VIP Erişim",
        'purchase_description': "Premium erişim için ödeme yapın",
        'successful_payment': "Ödeme Telegram tarafından rededildi! lütfen tekrar deneyiniz.",
        'name': "İsim",
        'surname': "Soyisim",
        'birthplace': "Doğum Yeri",
        'birth_date': "Doğum Tarihi",
        'age': "Yaş",
        'serial_no': "Seri No",
        'record_no': "Sicil No",
        'mother_name': "Anne Adı",
        'mother_id': "Anne T.C.",
        'father_name': "Baba Adı",
        'father_id': "Baba T.C.",
        'update_success': "✅ Bot başarıyla güncellendi!",
        'update_failed': "❌ Güncelleme başarısız oldu.",
        'update_no_access': "⛔ Bu komutu sadece bot sahibi kullanabilir."
    },
    'en': {
        'welcome_select': "Please select a language to use the bot:",
        'welcome': "👋 Hello! Welcome to the Phone Query Bot!\n\n"
                   "With this bot, you can learn certain information about phone numbers. To get information, please send a phone number.\n\n"
                   "📋 Features:\n"
                   "    ├📞 Query phone number information\n"
                   "    ├🔒 Premium access to hidden information\n"
                   "    └📍 Live location tracking (requires premium membership)\n\n"
                   "To start, send a phone number or click the 'Help' button below.",
        'help': "📖 <b>Help Menu</b>\n\nWith this bot, you can get information about various phone numbers.\n\n🔹 <b>How to Use:</b>\n    └ Send a phone number, and the bot will provide related information.\n\n🔹 <b>Commands:</b>\n    ├ /start - Shows the welcome message\n    ├ /help - Displays this help message\n    └ Phone number - Query information\n\n📲 Example:\nYou can query by sending a number like <i>+905555555555</i>.",
        'settings': "⚙️ <b>Settings</b>: Language Options",
        'settings_button': "⚙️ Settings",
        'help_button': "ℹ️ Help",
        'premium_button': "💎 Buy Premium",
        'back_button': "🔙 Back",
        'invalid_number': "❗ Invalid phone number format. Please send a valid phone number. example: +13405555555",
        'phone_info': "📞 <b>Phone Number Information:</b>",
        'country': "Country",
        'operator': "Operator",
        'timezones': "Time Zone",
        'number_type': "Number Type",
        'valid_number': "Valid Number",
        'national_number': "National Number",
        'area_code': "Area Code",
        'e164_format': "E164 Format",
        'person_info': "👤 <b>Personal Information (Hidden):</b>",
        'live_location_warning': "⚠️ <b>Live Location Tracking and All Personal Information</b>: Premium membership is required to access this information.\nContact our support team to get premium access.",
        'premium_required': "Requires Premium",
        'location_button': "📍See Location📍",
        'premium_warning': "You are not a premium member. Become a premium member to use this feature.",
        'purchase_title': "VIP Access",
        'purchase_description': "Make payment for premium access",
        'successful_payment': "Pay has been rejected by Telegram! please try again.",
        'name': "Name",
        'surname': "Surname",
        'birthplace': "Birthplace",
        'birth_date': "Birth Date",
        'age': "Age",
        'serial_no': "Serial No",
        'record_no': "Record No",
        'mother_name': "Mother's Name",
        'mother_id': "Mother's ID",
        'father_name': "Father's Name",
        'father_id': "Father's ID",
        'update_success': "✅ Bot updated successfully!",
        'update_failed': "❌ Update failed.",
        'update_no_access': "⛔ Only the bot owner can use this command."
    },
    'ar': {
        'welcome_select': "يرجى اختيار لغة لاستخدام البوت:",
        'welcome': "👋 مرحبًا! مرحبًا بك في بوت استعلام الهاتف!\n\n"
                   "مع هذا البوت، يمكنك معرفة معلومات معينة حول أرقام الهواتف. للحصول على المعلومات، يرجى إرسال رقم هاتف.\n\n"
                   "📋 الميزات:\n"
                   "    ├📞 استعلام عن معلومات رقم الهاتف\n"
                   "    ├🔒 وصول بريميوم إلى المعلومات المخفية\n"
                   "    └📍 تتبع الموقع المباشر (يتطلب عضوية بريميوم)\n\n"
                   "للبدء، أرسل رقم هاتف أو انقر على زر 'المساعدة' أدناه.",
        'help': "📖 <b>قائمة المساعدة</b>\n\nمع هذا البوت، يمكنك الحصول على معلومات حول أرقام الهواتف المختلفة.\n\n🔹 <b>كيفية الاستخدام:</b>\n    └ أرسل رقم هاتف وسيقدم البوت المعلومات ذات الصلة.\n\n🔹 <b>الأوامر:</b>\n    ├ /start - يظهر رسالة الترحيب\n    ├ /help - يعرض هذه الرسالة المساعدة\n    └ رقم الهاتف - استعلام عن المعلومات\n\n📲 مثال:\nيمكنك الاستعلام بإرسال رقم مثل <i>+905555555555</i>.",
        'settings': "⚙️ <b>الإعدادات</b>: خيارات اللغة",
        'settings_button': "⚙️ الإعدادات",
        'help_button': "ℹ️ مساعدة",
        'premium_button': "💎 شراء بريميوم",
        'back_button': "🔙 عودة",
        'invalid_number': "❗ تنسيق رقم هاتف غير صالح. يرجى إرسال رقم هاتف صالح. مثال: +13405555555",
        'phone_info': "📞 <b>معلومات رقم الهاتف:</b>",
        'country': "الدولة",
        'operator': "المشغل",
        'timezones': "المنطقة الزمنية",
        'number_type': "نوع الرقم",
        'valid_number': "رقم صالح",
        'national_number': "الرقم الوطني",
        'area_code': "رمز المنطقة",
        'e164_format': "تنسيق E164",
        'person_info': "👤 <b>المعلومات الشخصية (مخفية):</b>",
        'live_location_warning': "⚠️ <b>تتبع الموقع المباشر وجميع المعلومات الشخصية</b>: يتطلب عضوية بريميوم للوصول إلى هذه المعلومات.\nاتصل بفريق الدعم لدينا للحصول على وصول بريميوم.",
        'premium_required': "يتطلب بريميوم",
        'location_button': "📍انظر الموقع📍",
        'premium_warning': "أنت لست عضوًا مميزًا. كن عضوًا مميزًا لاستخدام هذه الميزة.",
        'purchase_title': "الوصول إلى VIP",
        'purchase_description': "قم بالدفع للوصول إلى البريميوم",
        'successful_payment': "تم رفض الدفع بواسطة برقية! يرجى المحاولة مرة أخرى.",
        'name': "الاسم",
        'surname': "اللقب",
        'birthplace': "مكان الميلاد",
        'birth_date': "تاريخ الميلاد",
        'age': "العمر",
        'serial_no': "الرقم التسلسلي",
        'record_no': "رقم السجل",
        'mother_name': "اسم الأم",
        'mother_id': "رقم هوية الأم",
        'father_name': "اسم الأب",
        'father_id': "رقم هوية الأب",
        'update_success': "✅ تم تحديث البوت بنجاح!",
        'update_failed': "❌ فشل التحديث.",
        'update_no_access': "⛔ فقط مالك البوت يمكنه استخدام هذا الأمر."
    },
    'ru': {
        'welcome_select': "Пожалуйста, выберите язык для использования бота:",
        'welcome': "👋 Привет! Добро пожаловать в Бот Запроса Телефонов!\n\n"
                   "С помощью этого бота вы можете узнать определенную информацию о номерах телефонов. Чтобы получить информацию, отправьте номер телефона.\n\n"
                   "📋 Возможности:\n"
                   "    ├📞 Запрос информации о номере телефона\n"
                   "    ├🔒 Премиум-доступ к скрытой информации\n"
                   "    └📍 Отслеживание живого местоположения (требуется премиум-подписка)\n\n"
                   "Чтобы начать, отправьте номер телефона или нажмите кнопку 'Помощь' ниже.",
        'help': "📖 <b>Меню Помощи</b>\n\nС помощью этого бота вы можете получить информацию о различных номерах телефонов.\n\n🔹 <b>Как использовать:</b>\n    └ Отправьте номер телефона, и бот предоставит связанную информацию.\n\n🔹 <b>Команды:</b>\n    ├ /start - Показать приветственное сообщение\n    ├ /help - Показать это сообщение помощи\n    └ Номер телефона - Запрос информации\n\n📲 Пример:\nВы можете запросить, отправив номер, как <i>+905555555555</i>.",
        'settings': "⚙️ <b>Настройки</b>: Языковые Опции",
        'settings_button': "⚙️ Настройки",
        'help_button': "ℹ️ Помощь",
        'premium_button': "💎 Купить Премиум",
        'back_button': "🔙 Назад",
        'invalid_number': "❗ Неверный формат номера телефона. Пожалуйста, отправьте действительный номер телефона. Пример: +13405555555",
        'phone_info': "📞 <b>Информация о номере телефона:</b>",
        'country': "Страна",
        'operator': "Оператор",
        'timezones': "Часовые Пояса",
        'number_type': "Тип Номера",
        'valid_number': "Действительный Номер",
        'national_number': "Национальный Номер",
        'area_code': "Код региона",
        'e164_format': "Формат E164",
        'person_info': "👤 <b>Личная информация (Скрыта):</b>",
        'live_location_warning': "⚠️ <b>Отслеживание местоположения и вся личная информация</b>: Премиум-подписка требуется для доступа к этой информации.\nСвяжитесь с нашей службой поддержки, чтобы получить премиум-доступ.",
        'premium_required': "Требуется Премиум",
        'location_button': "📍Посмотреть местоположение📍",
        'premium_warning': "Вы не являетесь премиум-участником. Станьте премиум-участником, чтобы использовать эту функцию.",
        'purchase_title': "VIP Доступ",
        'purchase_description': "Оплатите за доступ к премиуму",
        'successful_payment': "Оплата была отклонена Telegram! пожалуйста, попробуйте еще раз.",
        'name': "Имя",
        'surname': "Фамилия",
        'birthplace': "Место Рождения",
        'birth_date': "Дата Рождения",
        'age': "Возраст",
        'serial_no': "Серийный Номер",
        'record_no': "Номер записи",
        'mother_name': "Имя Матери",
        'mother_id': "ID Матери",
        'father_name': "Имя Отца",
        'father_id': "ID Отца",
        'update_success': "✅ Бот успешно обновлен!",
        'update_failed': "❌ Обновление не удалось.",
        'update_no_access': "⛔ Только владелец бота может использовать эту команду."

    },
    'hi': {
        'welcome_select': "कृपया बॉट का उपयोग करने के लिए एक भाषा चुनें:",
        'welcome': "👋 नमस्ते! फोन क्वेरी बॉट में आपका स्वागत है!\n\n"
                   "इस बॉट के साथ, आप फोन नंबरों के बारे में कुछ जानकारी प्राप्त कर सकते हैं। जानकारी प्राप्त करने के लिए कृपया एक फोन नंबर भेजें।\n\n"
                   "📋 विशेषताएं:\n"
                   "    ├📞 फोन नंबर जानकारी का अनुरोध\n"
                   "    ├🔒 छिपी हुई जानकारी के लिए प्रीमियम एक्सेस\n"
                   "    └📍 लाइव स्थान ट्रैकिंग (प्रीमियम सदस्यता आवश्यक है)\n\n"
                   "शुरू करने के लिए, एक फोन नंबर भेजें या नीचे 'सहायता' बटन पर क्लिक करें।",
        'help': "📖 <b>सहायता मेनू</b>\n\nइस बॉट के साथ, आप विभिन्न फोन नंबरों के बारे में जानकारी प्राप्त कर सकते हैं।\n\n🔹 <b>कैसे उपयोग करें:</b>\n    └ एक फोन नंबर भेजें, और बॉट संबंधित जानकारी प्रदान करेगा।\n\n🔹 <b>कमान्ड्स:</b>\n    ├ /start - स्वागत संदेश दिखाता है\n    ├ /help - यह सहायता संदेश दिखाता है\n    └ फोन नंबर - जानकारी का अनुरोध\n\n📲 उदाहरण:\nआप <i>+905555555555</i> जैसे एक नंबर भेजकर अनुरोध कर सकते हैं।",
        'settings': "⚙️ <b>सेटिंग्स</b>: भाषा विकल्प",
        'settings_button': "⚙️ सेटिंग्स",
        'help_button': "ℹ️ सहायता",
        'premium_button': "💎 प्रीमियम खरीदें",
        'back_button': "🔙 वापस",
        'invalid_number': "❗ अमान्य फ़ोन नंबर प्रारूप. कृपया एक मान्य फोन नंबर भेजें। उदाहरण: +13405555555",
        'phone_info': "📞 <b>फोन नंबर जानकारी:</b>",
        'country': "देश",
        'operator': "ऑपरेटर",
        'timezones': "समय क्षेत्र",
        'number_type': "नंबर का प्रकार",
        'valid_number': "वैध नंबर",
        'national_number': "राष्ट्रीय नंबर",
        'area_code': "क्षेत्र कोड",
        'e164_format': "E164 प्रारूप",
        'person_info': "👤 <b>व्यक्तिगत जानकारी (छिपा हुआ):</b>",
        'live_location_warning': "⚠️ <b>लाइव स्थान ट्रैकिंग और सभी व्यक्तिगत जानकारी</b>: इस जानकारी तक पहुँचने के लिए प्रीमियम सदस्यता आवश्यक है।\nप्रीमियम एक्सेस प्राप्त करने के लिए हमारे समर्थन टीम से संपर्क करें।",
        'premium_required': "प्रीमियम आवश्यक",
        'location_button': "📍स्थान देखें📍",
        'premium_warning': "आप प्रीमियम सदस्य नहीं हैं। इस सुविधा का उपयोग करने के लिए प्रीमियम सदस्य बनें।",
        'purchase_title': "VIP एक्सेस",
        'purchase_description': "प्रीमियम एक्सेस के लिए भुगतान करें",
        'successful_payment': "वेतन टेलीग्राम द्वारा अस्वीकार कर दिया गया है! कृपया पुनः प्रयास करें । ",
        'name': "नाम",
        'surname': "उपनाम",
        'birthplace': "जन्म स्थान",
        'birth_date': "जन्म तिथि",
        'age': "आयु",
        'serial_no': "सीरियल नंबर",
        'record_no': "रिकॉर्ड नंबर",
        'mother_name': "माँ का नाम",
        'mother_id': "माँ का आईडी",
        'father_name': "पिता का नाम",
        'father_id': "पिता का आईडी",
        'update_success': "✅ बॉट सफलतापूर्वक अपडेट किया गया!",
        'update_failed': "❌ अपडेट विफल रहा।",
        'update_no_access': "⛔ केवल बॉट मालिक ही इस कमांड का उपयोग कर सकता है।"
    }
}

BOT_OWNER_ID = 1897795912 

@bot.message_handler(commands=['update'])
def update_bot(message):
    if message.from_user.id == BOT_OWNER_ID:
        language = user_languages.get(message.from_user.id, 'en')
        try:
            # Git'ten en son değişiklikleri çek
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
            if result.returncode == 0:
                bot.reply_to(message, messages[language]['update_success'])
                # Botu yeniden başlat
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                bot.reply_to(message, f"{messages[language]['update_failed']}\nError: {result.stderr}")
        except Exception as e:
            bot.reply_to(message, f"{messages[language]['update_failed']}\nError: {str(e)}")
    else:
        language = user_languages.get(message.from_user.id, 'en')
        bot.reply_to(message, messages[language]['update_no_access'])

@bot.message_handler(commands=['prelist'])
def send_premium_list(message):
    if message.from_user.id == BOT_OWNER_ID:
        try:
            # premium_users.txt dosyasını okuma ve listeleme
            with open("premium_users.txt", "r") as file:
                premium_users = file.readlines()

            if premium_users:
                # Kullanıcı ID'lerini temizleyip mesaj halinde birleştime işlemi
                premium_list = ''.join(premium_users).strip()
                bot.send_message(message.chat.id, f"Premium Üyeler Listesi:\n{premium_list}")
            else:
                bot.send_message(message.chat.id, "Henüz premium üyeler yok.")

        except FileNotFoundError:
            bot.send_message(message.chat.id, "Premium üyeler listesi bulunamadı.")
    else:
        bot.send_message(message.chat.id, "Bu komutu sadece bot sahibi kullanabilir.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id not in user_languages:
        user_languages[user_id] = 'en'  # Varsayılan dil İngilizce siz değiştirebilirsiniz
        language = 'en'
        welcome_text = messages[language]['welcome_select']

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"))
        markup.add(types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
        markup.add(types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"))
        markup.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
        markup.add(types.InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi"))

        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")
    else:
        language = user_languages[user_id]
        show_main_menu(message.chat.id, language)

def show_main_menu(chat_id, language):
    welcome_text = messages[language]['welcome']
    markup = types.InlineKeyboardMarkup()
    settings_button = types.InlineKeyboardButton(messages[language]['settings_button'], callback_data="settings")
    help_button = types.InlineKeyboardButton(messages[language]['help_button'], callback_data="help")
    premium_button = types.InlineKeyboardButton(messages[language]['premium_button'], callback_data="buy_premium")
    markup.add(settings_button, help_button)
    markup.add(premium_button)
    bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def select_language(call):
    user_id = call.from_user.id
    selected_lang = call.data.split("_")[1]
    user_languages[user_id] = selected_lang

    language = user_languages[user_id]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_main_menu(call.message.chat.id, language)

@bot.callback_query_handler(func=lambda call: call.data == "buy_premium")
def buy_premium(call):
    user_id = call.from_user.id
    language = user_languages.get(user_id, 'en')

    # Ödeme bilgileri
    title = messages[language]['purchase_title']
    description = messages[language]['purchase_description']
    price = 1  # Fiyat sadece XTR cinsinden ayarlanabilir
    prices = [LabeledPrice(label=title, amount=price * 1000)]  # 1 birim için 100 ekleyin

    bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=description,
        invoice_payload="VIP Access",
        provider_token=PROVIDER_TOKEN,
        currency="XTR",
        prices=prices
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout_handler(pre_checkout_query: PreCheckoutQuery):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment_handler(message):
    user_id = message.from_user.id
    language = user_languages.get(user_id, 'en')
    success_message = messages[language]['successful_payment']

    # Premium üyeliği işaretleyin (örneğin bir veritabanında veya dosyada saklanabilir)
    with open("premium_users.txt", "a") as file:
        file.write(f"{user_id}\n")

    bot.send_message(user_id, success_message)

@bot.callback_query_handler(func=lambda call: call.data == "settings")
def settings(call):
    language = user_languages.get(call.from_user.id, 'en')
    settings_text = messages[language]['settings']

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"))
    markup.add(types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    markup.add(types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"))
    markup.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi"))

    bot.edit_message_text(settings_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "help")
def send_help(call):
    language = user_languages.get(call.from_user.id, 'en')
    help_text = messages[language]['help']

    markup = types.InlineKeyboardMarkup()
    premium_button = types.InlineKeyboardButton(messages[language]['premium_button'], callback_data="buy_premium")
    back_button = types.InlineKeyboardButton(messages[language]['back_button'], callback_data="back_to_welcome")
    markup.add(premium_button)
    markup.add(back_button)

    bot.edit_message_text(help_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_welcome")
def back_to_welcome(call):
    language = user_languages.get(call.from_user.id, 'en')
    welcome_text = messages[language]['welcome']

    markup = types.InlineKeyboardMarkup()
    settings_button = types.InlineKeyboardButton(messages[language]['settings_button'], callback_data="settings")
    help_button = types.InlineKeyboardButton(messages[language]['help_button'], callback_data="help")
    premium_button = types.InlineKeyboardButton(messages[language]['premium_button'], callback_data="buy_premium")
    markup.add(settings_button, help_button)
    markup.add(premium_button)

    bot.edit_message_text(welcome_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    language = user_languages.get(user_id, 'en')

    phone_number_text = message.text
    details = get_phone_number_details(phone_number_text)

    if details:
        message_text = (
            f"{messages[language]['phone_info']}\n"
            f"    ├🌍 <b>{messages[language]['country']}:</b> {details['country']}\n"
            f"    ├📶 <b>{messages[language]['operator']}:</b> {details['operator']}\n"
            f"    ├⏰ <b>{messages[language]['timezones']}:</b> {details['timezones']}\n"
            f"    ├🔢 <b>{messages[language]['number_type']}:</b> {details['number_type']}\n"
            f"    ├✅ <b>{messages[language]['valid_number']}:</b> {details['valid_number']}\n"
            f"    ├📍 <b>{messages[language]['national_number']}:</b> {details['national_number']}\n"
            f"    ├🗺 <b>{messages[language]['area_code']}:</b> {details['area_code']}\n"
            f"    └📞 <b>{messages[language]['e164_format']}:</b> {details['e164_format']}\n\n"
            f"{messages[language]['person_info']}\n"
            f"    ├🔒 <b>{messages[language]['name']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    ├🔒 <b>{messages[language]['surname']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    ├🔒 <b>{messages[language]['birthplace']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    ├🔒 <b>{messages[language]['birth_date']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    ├🔒 <b>{messages[language]['age']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    ├🔒 <b>{messages[language]['serial_no']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    ├🔒 <b>{messages[language]['record_no']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    ├🔒 <b>{messages[language]['mother_name']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    ├🔒 <b>{messages[language]['mother_id']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    ├🔒 <b>{messages[language]['father_name']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
            f"    └🔒 <b>{messages[language]['father_id']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n\n"
            f"{messages[language]['live_location_warning']}"
        )
        markup = types.InlineKeyboardMarkup()
        location_button = types.InlineKeyboardButton(messages[language]['location_button'], callback_data="view_location")
        markup.add(location_button)

        bot.reply_to(message, message_text, parse_mode="HTML", reply_markup=markup)
    else:
        bot.reply_to(message, messages[language]['invalid_number'])

@bot.callback_query_handler(func=lambda call: call.data == "view_location")
def location_access_warning(call):
    language = user_languages.get(call.from_user.id, 'en')
    premium_warning = messages[language]['premium_warning']
    bot.answer_callback_query(call.id, premium_warning, show_alert=True)

def get_phone_number_details(number):
    try:
        phone_number = phonenumbers.parse(number)
        if not phonenumbers.is_valid_number(phone_number):
            return None

        details = {
            'country': geocoder.description_for_number(phone_number, "en") or "Unknown",
            'operator': carrier.name_for_number(phone_number, "en") or "Unknown",
            'timezones': ", ".join(timezone.time_zones_for_number(phone_number)) or "Unknown",
            'number_type': phonenumbers.number_type(phone_number),
            'valid_number': phonenumbers.is_valid_number(phone_number),
            'national_number': phonenumbers.national_significant_number(phone_number),
            'area_code': phonenumbers.region_code_for_number(phone_number),
            'e164_format': phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
        }
        return details

    except NumberParseException:
        return None







@bot.callback_query_handler(func=lambda call: call.data == "ss7_exploit")
def handle_ss7_exploit(call):
    user_id = call.from_user.id
    language = user_languages.get(user_id, 'en')
    
    if not is_premium_user(user_id):
        bot.answer_callback_query(call.id, "🔒 Bu özellik sadece VIP üyelere açıktır", show_alert=True)
        return
    
    # SS7 exploit onayı
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ SS7 Exploit Başlat", callback_data="confirm_ss7"))
    markup.add(types.InlineKeyboardButton("❌ İptal", callback_data="cancel_ss7"))
    
    warning_text = """
🔴 <b>SS7 EXPLOIT SİSTEMİ - KRİTİK UYARI</b>

⚠️ <b>BU ÖZELLİK İLE:</b>
• GSM ağ altyapısına erişim sağlanır
• IMSI ve konum bilgileri çekilir
• Abone verilerine erişilir

⚖️ <b>YASAL DURUM:</b>
• Telekomünikasyon altyapısına izinsiz erişim
• 5809 sayılı Elektronik Haberleşme Kanunu ihlali
• Ağır cezai yaptırımlar uygulanır

✅ Devam etmek için onay verin:
"""
    
    bot.edit_message_text(
        warning_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "confirm_ss7")
def start_ss7_exploit(call):
    user_id = call.from_user.id
    language = user_languages.get(user_id, 'en')
    
    bot.edit_message_text(
        "🛰️ <b>SS7 Exploit Sistemi Başlatılıyor...</b>\n\n"
        "Lütfen hedef telefon numarasını gönderin:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )
    
    # Kullanıcı durumunu güncelle
    user_states[user_id] = 'awaiting_ss7_number'

# Kullanıcı durum takibi
user_states = {}

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_ss7_number')
def handle_ss7_number(message):
    user_id = message.from_user.id
    phone_number = message.text
    
    # SS7 exploit başlat
    bot.send_message(message.chat.id, "🛰️ <b>SS7 Exploit Çalıştırılıyor...</b>", parse_mode="HTML")
    
    gsm_exploiter = GSMNetworkExploiter()
    
    # IMSI sorgula
    imsi_data = gsm_exploiter.get_subscriber_imsi(phone_number)
    
    # Konum bilgisi
    location_data = gsm_exploiter.get_real_time_location(phone_number)
    
    # Abone bilgisi
    subscriber_data = gsm_exploiter.get_subscriber_info(phone_number)
    
    # Sonuçları göster
    report = generate_ss7_report(phone_number, imsi_data, location_data, subscriber_data)
    send_ss7_report(message.chat.id, report, user_languages.get(user_id, 'en'))
    
    # Durumu temizle
    user_states[user_id] = None

def generate_ss7_report(phone_number, imsi_data, location_data, subscriber_data):
    """SS7 exploit raporu oluştur"""
    return {
        'phone_number': phone_number,
        'exploit_timestamp': datetime.now().isoformat(),
        'imsi_info': imsi_data,
        'location_info': location_data,
        'subscriber_info': subscriber_data,
        'network_info': {
            'mcc': 286,
            'mnc': 1,
            'operator': 'Turkcell',
            'technology': 'GSM/LTE'
        },
        'security_warning': 'BU RAPOR EĞİTİM AMAÇLIDIR - GERÇEK VERİ DEĞİLDİR'
    }

def send_ss7_report(chat_id, report, language):
    """SS7 raporunu gönder"""
    report_text = f"""
🛰️ <b>SS7 EXPLOIT RAPORU</b>

📞 <b>Hedef Numara:</b> {report['phone_number']}
⏰ <b>Sorgu Zamanı:</b> {report['exploit_timestamp']}

🔍 <b>IMSI Bilgileri:</b>
├ IMSI: {report['imsi_info']['imsi'] if report['imsi_info'] else 'N/A'}
├ Ülke Kodu: {report['imsi_info']['country_code'] if report['imsi_info'] else 'N/A'}
├ Ağ Kodu: {report['imsi_info']['network_code'] if report['imsi_info'] else 'N/A'}
└ Abone ID: {report['imsi_info']['subscriber_id'] if report['imsi_info'] else 'N/A'}

📍 <b>Konum Bilgisi:</b>
├ Enlem: {report['location_info']['coordinates']['latitude'] if report['location_info'] else 'N/A'}
├ Boylam: {report['location_info']['coordinates']['longitude'] if report['location_info'] else 'N/A'}
├ Doğruluk: {report['location_info']['coordinates']['range'] if report['location_info'] else 'N/A'}m
├ LAC: {report['location_info']['cell_location']['lac'] if report['location_info'] else 'N/A'}
└ Cell ID: {report['location_info']['cell_location']['cell_id'] if report['location_info'] else 'N/A'}

📡 <b>Ağ Bilgisi:</b>
├ Operatör: {report['network_info']['operator']}
├ MCC: {report['network_info']['mcc']}
├ MNC: {report['network_info']['mnc']}
└ Teknoloji: {report['network_info']['technology']}

⚠️ <b>UYARI:</b> Bu veriler simülasyondur. Gerçek SS7 exploit yasa dışıdır.
"""
    
    # Konum haritası gönder
    if report['location_info']:
        map_img = generate_ss7_map(
            report['location_info']['coordinates']['latitude'],
            report['location_info']['coordinates']['longitude']
        )
        bot.send_photo(chat_id, map_img, caption=report_text, parse_mode="HTML")
    else:
        bot.send_message(chat_id, report_text, parse_mode="HTML")






logo2 = '''
88  dP 88 88b 88  dP""b8      dP"Yb  8888b.  88 88b 88
88odP  88 88Yb88 dP   `"     dP   Yb  8I  Yb 88 88Yb88
88"Yb  88 88 Y88 Yb  "88     Yb   dP  8I  dY 88 88 Y88
88  Yb 88 88  Y8  YboodP      YbodP  8888Y"  88 88  Y8
'''

print('bot çalışıyor')

import random

logo = '''
⠛⠛⣿⣿⣿⣿⣿⡷⢶⣦⣶⣶⣤⣤⣤⣀⠀⠀⠀
⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⠀
⠀⠀⠀⠉⠉⠉⠙⠻⣿⣿⠿⠿⠛⠛⠛⠻⣿⣿⣇⠀
⠀⠀⢤🔥⣀⠀⠀⢸⣷⡄⠀🔥⣀⣤⣴⣿⣿⣿⣆
⠀⠀⠀⠹⠏⠀⠀⠀⣿⣧⠀⠹⣿⣿⣿⣿⣿⡿⣿
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠛⠿⠇⢀⣼⣿⣿⠛⢯⡿⡟
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠦⠴⢿⢿⣿⡿⠷⠀⣿⠀
⠀⠀⠀⠀⠀⠀⠀⠙⣷⣶⣶⣤⣤⣤⣤⣤⣶⣦⠃⠀
⠀⠀⠀⠀⠀⠀⠀⢐⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠻⢿⣿⣿⣿⣿⠟⠁
TELEGRAM | @KingOdi
'''
colors = [
    "\033[91m", "\033[94m", "\033[92m", "\033[93m", "\033[38;5;208m",
    "\033[95m", "\033[97m", "\033[37m"
]
random_color = random.choice(colors)
print(random_color + logo + logo2)

def main():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Hata oluştu: {e}")
            time.sleep(15)

if __name__ == '__main__':
    main()




