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
import random
import hashlib
import json
from faker import Faker

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
PROVIDER_TOKEN = os.getenv('PROVIDER_TOKEN')

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

bot = TeleBot(TOKEN)

# Fake data generator
fake = Faker()

user_languages = {}
user_consents = {}
user_states = {}

# Premium kullanıcı kontrolü - SADECE TXT/JSON
def is_premium_user(user_id):
    user_id_str = str(user_id)
    
    # 1. Önce premium_users.txt'yi kontrol et
    try:
        with open("premium_users.txt", "r") as file:
            premium_users = file.read().splitlines()
            if user_id_str in premium_users:
                return True
    except:
        pass
    
    # 2. premium_users.json'ı kontrol et
    try:
        with open("premium_users.json", "r") as file:
            premium_data = json.load(file)
            if user_id_str in premium_data:
                # Süre kontrolü yap
                premium_until = datetime.fromisoformat(premium_data[user_id_str]['premium_until'])
                return premium_until > datetime.now()
    except:
        pass
    
    return False

# Premium kullanıcı ekleme
def add_premium_user_to_files(user_id, days=30):
    user_id_str = str(user_id)
    premium_until = datetime.now() + timedelta(days=days)
    
    # 1. premium_users.txt'ye ekle
    try:
        with open("premium_users.txt", "r") as file:
            existing_users = file.read().splitlines()
    except:
        existing_users = []
    
    if user_id_str not in existing_users:
        with open("premium_users.txt", "a") as file:
            file.write(f"{user_id_str}\n")
    
    # 2. premium_users.json'a ekle (detaylı bilgi için)
    try:
        with open("premium_users.json", "r") as file:
            premium_data = json.load(file)
    except:
        premium_data = {}
    
    premium_data[user_id_str] = {
        'added_date': datetime.now().isoformat(),
        'premium_until': premium_until.isoformat(),
        'days': days,
        'added_by': 'admin'
    }
    
    with open("premium_users.json", "w") as file:
        json.dump(premium_data, file, indent=4)
    
    return premium_until

# Premium kullanıcı kaldırma
def remove_premium_user_from_files(user_id):
    user_id_str = str(user_id)
    
    # 1. premium_users.txt'den kaldır
    try:
        with open("premium_users.txt", "r") as file:
            lines = file.readlines()
        with open("premium_users.txt", "w") as file:
            for line in lines:
                if line.strip() != user_id_str:
                    file.write(line)
    except:
        pass
    
    # 2. premium_users.json'dan kaldır
    try:
        with open("premium_users.json", "r") as file:
            premium_data = json.load(file)
        
        if user_id_str in premium_data:
            del premium_data[user_id_str]
            
        with open("premium_users.json", "w") as file:
            json.dump(premium_data, file, indent=4)
    except:
        pass

# Sorgu geçmişi kaydetme
def log_query(user_id, phone_number, query_type):
    try:
        with open("query_history.json", "r") as file:
            history = json.load(file)
    except:
        history = []
    
    history.append({
        'user_id': user_id,
        'phone_number': phone_number,
        'query_type': query_type,
        'timestamp': datetime.now().isoformat()
    })
    
    with open("query_history.json", "w") as file:
        json.dump(history, file, indent=4)

messages = {
    'tr': {
        'welcome_select': "Lütfen botu kullanmak için bir dil seçin:",
        'welcome': "👋 Merhaba! Gelişmiş Telefon Sorgu Botu'na hoş geldiniz!\n\n"
                   "Bu bot ile telefon numaralarına ait gelişmiş bilgilere erişebilirsiniz.\n\n"
                   "📋 Özellikler:\n"
                   "    ├📞 Temel telefon bilgileri\n"
                   "    ├🔒 Gizli kişi bilgileri\n"
                   "    ├📍 Canlı konum izleme\n"
                   "    └🛰️ SS7 Exploit sistemi\n\n"
                   "Başlamak için bir telefon numarası gönderin.",
        'help': "📖 <b>Yardım Menüsü</b>\n\nBu bot ile gelişmiş telefon numarası bilgilerine erişebilirsiniz.\n\n🔹 <b>Nasıl Kullanılır:</b>\n    └ Bir telefon numarası gönderin, bot size detaylı bilgileri iletsin.\n\n🔹 <b>Komutlar:</b>\n    ├ /start - Karşılama mesajını gösterir\n    ├ /help - Bu yardım mesajını gösterir\n    └ Telefon numarası - Bilgi sorgulama\n\n📲 Örnek kullanım:\n<i>+905555555555</i> gibi bir numara göndererek sorgulama yapabilirsiniz.",
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
        'live_location_warning': "⚠️ <b>Canlı Konum İzleme ve Tüm Kişi Bilgileri</b>: Bu bilgilere erişmek için premium üyelik gereklidir.",
        'premium_required': "Premium gerektirir",
        'location_button': "📍Konumu Gör📍",
        'premium_warning': "Premium üye değilsiniz. Bu özelliği kullanmak için premium üye olun.",
        'purchase_title': "VIP Erişim",
        'purchase_description': "Premium erişim için ödeme yapın",
        'successful_payment': "✅ Premium üyelik aktif edildi!",
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
        'update_no_access': "⛔ Bu komutu sadece bot sahibi kullanabilir.",
        'ss7_button': "🛰️ SS7 Exploit",
        'ss7_warning': "🔴 SS7 EXPLOIT SİSTEMİ - KRİTİK UYARI",
        'ss7_confirm': "✅ SS7 Exploit Başlat",
        'ss7_cancel': "❌ İptal",
        'legal_consent': "✅ Yasal Onay ve Sorumluluk Kabulü",
        'update_start': "🔄 Bot güncellemesi başlatılıyor...",
        'update_details': "📊 Güncelleme Detayları",
        'update_packages': "📦 Paket Güncellemeleri"
    },
    'en': {
        'welcome_select': "Please select a language to use the bot:",
        'welcome': "👋 Hello! Welcome to Advanced Phone Query Bot!\n\n"
                   "With this bot, you can access advanced information about phone numbers.\n\n"
                   "📋 Features:\n"
                   "    ├📞 Basic phone information\n"
                   "    ├🔒 Hidden personal information\n"
                   "    ├📍 Live location tracking\n"
                   "    └🛰️ SS7 Exploit system\n\n"
                   "To start, send a phone number.",
        'help': "📖 <b>Help Menu</b>\n\nWith this bot, you can access advanced phone number information.\n\n🔹 <b>How to Use:</b>\n    └ Send a phone number, and the bot will provide detailed information.\n\n🔹 <b>Commands:</b>\n    ├ /start - Shows the welcome message\n    ├ /help - Displays this help message\n    └ Phone number - Query information\n\n📲 Example:\nYou can query by sending a number like <i>+905555555555</i>.",
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
        'live_location_warning': "⚠️ <b>Live Location Tracking and All Personal Information</b>: Premium membership is required to access this information.",
        'premium_required': "Requires Premium",
        'location_button': "📍See Location📍",
        'premium_warning': "You are not a premium member. Become a premium member to use this feature.",
        'purchase_title': "VIP Access",
        'purchase_description': "Make payment for premium access",
        'successful_payment': "✅ Premium membership activated!",
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
        'update_no_access': "⛔ Only the bot owner can use this command.",
        'ss7_button': "🛰️ SS7 Exploit",
        'ss7_warning': "🔴 SS7 EXPLOIT SYSTEM - CRITICAL WARNING",
        'ss7_confirm': "✅ Start SS7 Exploit",
        'ss7_cancel': "❌ Cancel",
        'legal_consent': "✅ Legal Consent and Responsibility Acceptance",
        'update_start': "🔄 Starting bot update...",
        'update_details': "📊 Update Details",
        'update_packages': "📦 Package Updates"
    }
}

BOT_OWNER_ID = 1897795912 

# Güncelleme fonksiyonları
def update_requirements():
    """requirements.txt dosyasını güncelle"""
    try:
        # Mevcut paketleri listele
        result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            with open('requirements.txt', 'w') as f:
                f.write(result.stdout)
            return True
    except Exception as e:
        print(f"Requirements güncelleme hatası: {e}")
    return False

def parse_git_output(output):
    """Git çıktısını parse et ve detaylı bilgi çıkar"""
    lines = output.split('\n')
    changes = {
        'files_modified': 0,
        'files_added': 0,
        'files_deleted': 0,
        'insertions': 0,
        'deletions': 0,
        'packages_updated': []
    }
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Dosya değişiklikleri
        if line.startswith('|'):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    changes['files_modified'] += 1
                    # Insertion/deletion sayılarını çıkar
                    for part in parts:
                        if part.startswith('+') and part[1:].isdigit():
                            changes['insertions'] += int(part[1:])
                        elif part.startswith('-') and part[1:].isdigit():
                            changes['deletions'] += int(part[1:])
                except:
                    pass
        # Yeni dosyalar
        elif 'create mode' in line:
            changes['files_added'] += 1
        # Silinen dosyalar
        elif 'delete mode' in line:
            changes['files_deleted'] += 1
        # Paket güncellemeleri
        elif 'requirements.txt' in line and '|' in line:
            changes['packages_updated'] = get_updated_packages()
    
    return changes

def get_updated_packages():
    """Güncellenen paketleri kontrol et"""
    try:
        # Eski ve yeni requirements karşılaştırması
        if os.path.exists('requirements.txt.old'):
            with open('requirements.txt.old', 'r') as f:
                old_req = f.read().splitlines()
            with open('requirements.txt', 'r') as f:
                new_req = f.read().splitlines()
            
            updated = []
            for old_line, new_line in zip(old_req, new_req):
                if old_line != new_line and '==' in old_line and '==' in new_line:
                    old_pkg = old_line.split('==')[0]
                    new_pkg = new_line.split('==')[0]
                    if old_pkg == new_pkg:
                        old_ver = old_line.split('==')[1]
                        new_ver = new_line.split('==')[1]
                        if old_ver != new_ver:
                            updated.append(f"{old_pkg} {old_ver} → {new_ver}")
            return updated
    except:
        pass
    return []

@bot.message_handler(commands=['update'])
def update_bot(message):
    if message.from_user.id != BOT_OWNER_ID:
        language = user_languages.get(message.from_user.id, 'en')
        bot.reply_to(message, messages[language]['update_no_access'])
        return
    
    language = user_languages.get(message.from_user.id, 'en')
    
    try:
        # Güncelleme başlangıç mesajı
        bot.reply_to(message, f"🔄 {messages[language]['update_start']}")
        
        # Requirements dosyasını yedekle
        if os.path.exists('requirements.txt'):
            os.rename('requirements.txt', 'requirements.txt.old')
        
        # Git'ten en son değişiklikleri çek
        pull_result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
        
        if pull_result.returncode == 0:
            # Git çıktısını parse et
            changes = parse_git_output(pull_result.stdout)
            
            # Requirements.txt'yi güncelle
            requirements_updated = update_requirements()
            
            # Detaylı güncelleme mesajı oluştur
            update_message = f"✅ **{messages[language]['update_success']}**\n\n"
            update_message += f"📊 **{messages[language]['update_details']}:**\n"
            update_message += "```\n"
            update_message += f"📁 Dosya Değişiklikleri:\n"
            update_message += f"   ├ 📝 Değiştirilen: {changes['files_modified']} dosya\n"
            update_message += f"   ├ ➕ Eklenen: {changes['files_added']} dosya\n"
            update_message += f"   ├ ➖ Silinen: {changes['files_deleted']} dosya\n"
            update_message += f"   ├ 📈 Insertions: +{changes['insertions']}\n"
            update_message += f"   └ 📉 Deletions: -{changes['deletions']}\n"
            
            if requirements_updated:
                update_message += f"\n📦 **{messages[language]['update_packages']}:**\n"
                updated_packages = get_updated_packages()
                if updated_packages:
                    for pkg in updated_packages[:5]:
                        update_message += f"   ├ {pkg}\n"
                    if len(updated_packages) > 5:
                        update_message += f"   └ ... ve {len(updated_packages) - 5} paket daha\n"
                else:
                    update_message += "   └ Tüm paketler güncel ✅\n"
            
            update_message += "```\n"
            
            # Git çıktısını da ekle (kısaltılmış)
            git_output_lines = pull_result.stdout.split('\n')
            important_lines = []
            for line in git_output_lines:
                if any(x in line for x in ['|', 'create', 'delete', 'Updating', 'Fast-forward']):
                    important_lines.append(line)
            
            if important_lines:
                update_message += "\n🔧 **Git Çıktısı:**\n"
                update_message += "```\n"
                for line in important_lines[:10]:
                    update_message += f"{line}\n"
                update_message += "```\n"
            
            bot.reply_to(message, update_message, parse_mode="Markdown")
            
            # Botu yeniden başlat
            time.sleep(2)
            os.execv(sys.executable, [sys.executable] + sys.argv)
            
        else:
            error_msg = f"❌ {messages[language]['update_failed']}\n"
            error_msg += f"**Hata:**\n```\n{pull_result.stderr}\n```"
            bot.reply_to(message, error_msg, parse_mode="Markdown")
            
    except Exception as e:
        error_msg = f"❌ {messages[language]['update_failed']}\n"
        error_msg += f"**Exception:**\n```\n{str(e)}\n```"
        bot.reply_to(message, error_msg, parse_mode="Markdown")

@bot.message_handler(commands=['requirements'])
def manage_requirements(message):
    if message.from_user.id != BOT_OWNER_ID:
        return
    
    try:
        # requirements.txt oluştur veya güncelle
        if update_requirements():
            with open('requirements.txt', 'r') as f:
                requirements_content = f.read()
            
            # Dosyayı Telegram'dan gönder
            with open('requirements.txt', 'rb') as file:
                bot.send_document(message.chat.id, file, caption="📦 Güncel requirements.txt dosyası")
            
            # Paket istatistikleri
            package_count = len([line for line in requirements_content.split('\n') if line.strip() and not line.startswith('#')])
            bot.reply_to(message, f"✅ requirements.txt güncellendi!\n📊 Toplam {package_count} paket listelendi.")
        else:
            bot.reply_to(message, "❌ requirements.txt güncellenemedi!")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['install'])
def install_requirements(message):
    if message.from_user.id != BOT_OWNER_ID:
        return
    
    try:
        bot.reply_to(message, "📦 Paketler yükleniyor...")
        
        # requirements.txt'den paketleri yükle
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            success_msg = "✅ Paketler başarıyla yüklendi!\n\n"
            
            # Yüklenen paketleri parse et
            output_lines = result.stdout.split('\n')
            installed_packages = []
            for line in output_lines:
                if 'Successfully installed' in line:
                    packages = line.replace('Successfully installed', '').strip().split()
                    installed_packages.extend(packages)
                elif 'Requirement already satisfied' in line:
                    pkg_name = line.split('Requirement already satisfied:')[1].split(' ')[0].strip()
                    installed_packages.append(f"{pkg_name} (zaten yüklü)")
            
            if installed_packages:
                success_msg += "📦 **Yüklenen Paketler:**\n"
                for pkg in installed_packages[:10]:
                    success_msg += f"   ├ {pkg}\n"
                if len(installed_packages) > 10:
                    success_msg += f"   └ ... ve {len(installed_packages) - 10} paket daha\n"
            
            bot.reply_to(message, success_msg, parse_mode="Markdown")
        else:
            error_msg = "❌ Paket yükleme başarısız!\n"
            error_msg += f"**Hata:**\n```\n{result.stderr}\n```"
            bot.reply_to(message, error_msg, parse_mode="Markdown")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# SS7 Exploit Sınıfı
class SS7Exploiter:
    def __init__(self):
        self.ss7_gateway = "simulated_gateway"
        
    def get_subscriber_imsi(self, phone_number):
        """IMSI numarasını simüle et"""
        time.sleep(2)
        msisdn = phone_number.replace('+', '').replace('90', '')
        imsi = "28601" + msisdn.zfill(10)
        return {
            'imsi': imsi,
            'country_code': '286',
            'network_code': '01',
            'subscriber_id': msisdn
        }
    
    def get_real_time_location(self, phone_number):
        """Gerçek zamanlı konum bilgisi simülasyonu"""
        time.sleep(3)
        return {
            'cell_location': {
                'lac': random.randint(1000, 9999),
                'cell_id': random.randint(10000, 99999),
                'mcc': 286,
                'mnc': 1
            },
            'coordinates': {
                'latitude': round(random.uniform(36.0, 42.0), 6),
                'longitude': round(random.uniform(26.0, 45.0), 6),
                'range': random.randint(100, 2000)
            },
            'accuracy': '50-500 meters',
            'technology': 'GSM/LTE Triangulation',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_subscriber_info(self, phone_number):
        """Abone bilgisi simülasyonu"""
        time.sleep(1)
        return {
            'status': random.choice(['Active', 'Inactive']),
            'line_type': random.choice(['Prepaid', 'Postpaid']),
            'activation_date': fake.date_between(start_date='-5y', end_date='today').strftime('%d/%m/%Y'),
            'balance': f"{random.randint(0, 100)} TL"
        }

# GSM Ağ Bilgisi Sınıfı
class GSMNetworkExploiter:
    def __init__(self):
        self.ss7 = SS7Exploiter()
    
    def get_network_data(self, phone_number):
        """Tüm ağ verilerini topla"""
        bot.send_message('🔄️ sorgu alındı bekleyin...')
        
        imsi_data = self.ss7.get_subscriber_imsi(phone_number)
        location_data = self.ss7.get_real_time_location(phone_number)
        subscriber_data = self.ss7.get_subscriber_info(phone_number)
        
        return {
            'imsi_info': imsi_data,
            'location_info': location_data,
            'subscriber_info': subscriber_data,
            'network_info': {
                'mcc': 286,
                'mnc': 1,
                'operator': 'Turkcell',
                'technology': 'GSM/LTE'
            }
        }

# Kişisel Veri Sınıfı
class PersonalDataFetcher:
    def __init__(self):
        self.fake = Faker('tr_TR')
    
    def get_person_info(self, phone_number):
        """Kişi bilgileri simülasyonu"""
        time.sleep(2)
        return {
            'name': self.fake.first_name(),
            'surname': self.fake.last_name(),
            'birthplace': self.fake.city(),
            'birth_date': self.fake.date_of_birth(minimum_age=18, maximum_age=70).strftime('%d/%m/%Y'),
            'age': random.randint(18, 70),
            'mother_name': self.fake.first_name_female(),
            'father_name': self.fake.first_name_male(),
            'tc_identity': self.fake.random_number(digits=11, fix_len=True),
            'registration_city': self.fake.city()
        }
    
    def get_social_media_profiles(self, phone_number):
        """Sosyal medya profilleri simülasyonu"""
        platforms = ['WhatsApp', 'Telegram', 'Instagram', 'Facebook']
        found_profiles = random.sample(platforms, random.randint(1, 3))
        
        profiles = {}
        for platform in found_profiles:
            profiles[platform] = {
                'username': self.fake.user_name(),
                'last_seen': self.fake.date_time_this_month().strftime('%d/%m/%Y %H:%M'),
                'profile_status': random.choice(['Active', 'Inactive'])
            }
        
        return profiles

# Gelişmiş Sorgu Sistemi
def enhanced_phone_query(phone_number, user_id):
    """Gelişmiş telefon sorgulama"""
    basic_info = get_phone_number_details(phone_number)
    if not basic_info:
        return None
    
    log_query(user_id, phone_number, "basic_query")
    
    premium_features = {}
    if is_premium_user(user_id):
        gsm_exploiter = GSMNetworkExploiter()
        network_data = gsm_exploiter.get_network_data(phone_number)
        
        personal_fetcher = PersonalDataFetcher()
        person_info = personal_fetcher.get_person_info(phone_number)
        social_profiles = personal_fetcher.get_social_media_profiles(phone_number)
        
        premium_features = {
            'person_info': person_info,
            'social_profiles': social_profiles,
            'network_data': network_data,
            'risk_score': random.randint(1, 100),
            'data_confidence': f"%{random.randint(75, 95)}"
        }
        
        log_query(user_id, phone_number, "premium_query")
    
    return {
        'basic_info': basic_info,
        'premium_info': premium_features,
        'query_timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'query_id': hashlib.md5(f"{phone_number}{datetime.now()}".encode()).hexdigest()[:8].upper()
    }

# YENİ KONUM FONKSİYONLARI
@bot.callback_query_handler(func=lambda call: call.data.startswith("location_"))
def send_real_location(call):
    user_id = call.from_user.id
    language = user_languages.get(user_id, 'en')
    
    if not is_premium_user(user_id):
        bot.answer_callback_query(call.id, messages[language]['premium_warning'], show_alert=True)
        return
    
    try:
        # Rastgele İstanbul koordinatları oluştur
        istanbul_coordinates = [
            (41.0082, 28.9784),   # Sultanahmet
            (41.0406, 28.9861),   # Taksim
            (41.0151, 28.9795),   # Beyoğlu
            (41.0553, 29.0214),   # Beşiktaş
            (41.0765, 29.0527),   # Sarıyer
            (40.9923, 29.1244),   # Kadıköy
            (40.9615, 29.1135),   # Maltepe
            (41.0053, 28.9070),   # Bakırköy
            (41.0930, 28.8020),   # Arnavutköy
            (41.1821, 28.8814)    # Eyüpsultan
        ]
        
        lat, lon = random.choice(istanbul_coordinates)
        
        # Küçük rastgele offset ekle (daha gerçekçi olsun)
        lat += random.uniform(-0.01, 0.01)
        lon += random.uniform(-0.01, 0.01)
        
        # Konum bilgisi mesajı
        location_info = f"""
📍 <b>Gerçek Zamanlı Konum Bilgisi</b>

📱 <b>Hedef Cihaz:</b> Akıllı Telefon
📶 <b>Sinyal Gücü:</b> %{random.randint(65, 95)}
🕒 <b>Son Güncelleme:</b> {datetime.now().strftime('%H:%M:%S')}
🎯 <b>Doğruluk:</b> {random.randint(10, 50)} metre

🏢 <b>Tahmini Konum:</b>
├ 📍 İstanbul, Türkiye
├ 🏬 {random.choice(['AVM', 'İş Merkezi', 'Restoran', 'Kafe', 'Ev', 'Ofis'])}
└ 📶 {random.choice(['WiFi', 'GSM', 'LTE', '5G'])}

⚠️ <i>Konum verileri simülasyon amaçlıdır.</i>
"""
        
        # Önce konumu gönder
        bot.send_location(
            chat_id=call.message.chat.id,
            latitude=lat,
            longitude=lon,
            live_period=3600  # 1 saat canlı konum
        )
        
        # Sonra konum bilgilerini gönder
        bot.send_message(
            call.message.chat.id,
            location_info,
            parse_mode="HTML"
        )
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Konum gönderilemedi: {str(e)}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("details_"))
def send_detailed_info(call):
    user_id = call.from_user.id
    language = user_languages.get(user_id, 'en')
    
    if not is_premium_user(user_id):
        bot.answer_callback_query(call.id, messages[language]['premium_warning'], show_alert=True)
        return
    
    try:
        # Detaylı kişi bilgileri
        personal_fetcher = PersonalDataFetcher()
        person_info = personal_fetcher.get_person_info("+905555555555")
        social_profiles = personal_fetcher.get_social_media_profiles("+905555555555")
        
        details_text = f"""
👤 <b>Detaylı Kişi Bilgileri</b>

📋 <b>Kimlik Bilgileri:</b>
├ {messages[language]['name']}: {person_info['name']}
├ {messages[language]['surname']}: {person_info['surname']}
├ Doğum Tarihi: {person_info['birth_date']}
├ Yaş: {person_info['age']}
└ Doğum Yeri: {person_info['birthplace']}

🏠 <b>Kayıt Bilgileri:</b>
├ TC Kimlik: {person_info['tc_identity']}
├ Nüfuz İl: {person_info['registration_city']}
└ Medeni Hal: {random.choice(['Bekar', 'Evli'])}

👨‍👩‍👧‍👦 <b>Aile Bilgileri:</b>
├ Anne Adı: {person_info['mother_name']}
└ Baba Adı: {person_info['father_name']}

📱 <b>Sosyal Medya Profilleri:</b>
"""
        
        for platform, data in social_profiles.items():
            details_text += f"├ {platform}: {data['username']}\n"
            details_text += f"│ └ Son Giriş: {data['last_seen']}\n"
        
        details_text += f"""
📊 <b>Veri Güvenilirliği:</b> %{random.randint(85, 98)}

⚠️ <i>Bu bilgiler gizlidir paylaşmanızı önermeyiz.</i>
"""
        
        bot.send_message(
            call.message.chat.id,
            details_text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Detaylar gönderilemedi: {str(e)}", show_alert=True)

# Yasal Uyarı Sistemi
def send_legal_warning(chat_id, language):
    warning_text = {
        'tr': """
⚖️ <b>YASAL UYARI VE ONAY</b>

🔴 <b>BU BOTUN KULLANIMI İLE İLGİLİ ÖNEMLİ UYARILAR:</b>

• Bu bot gelişmiş kişisel verilere erişim sağlamaktadır
• 6698 sayılı KVKK'ya göre kişisel verileri izinsiz işlemek SUÇTUR
• Tüm sorumluluk kullanıcıya aittir
• Yasa dışı kullanımda cezai yaptırımlar uygulanır

✅ Devam etmek için aşağıdaki butona basarak:
• Tüm sorumluluğu kabul ettiğinizi
• Yasalara aykırı kullanımdan doğacak tüm sonuçlardan kendinizin sorumlu olduğunuzu
• 18 yaşından büyük olduğunuzu beyan edersiniz

👇 <b>Onaylamak için butona basın:</b>
""",
        'en': """
⚖️ <b>LEGAL WARNING AND CONSENT</b>

🔴 <b>IMPORTANT WARNINGS ABOUT USING THIS BOT:</b>

• This bot provides access to advanced personal data
• Processing personal data without permission is a CRIME
• All responsibility belongs to the user
• Criminal sanctions apply for illegal use

✅ By clicking the button below you confirm:
• You accept all responsibility
• You are responsible for all consequences of illegal use
• You declare that you are over 18 years old

👇 <b>Click the button to confirm:</b>
"""
    }
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(messages[language]['legal_consent'], callback_data="legal_consent"))
    
    bot.send_message(chat_id, warning_text.get(language, warning_text['tr']), 
                    parse_mode="HTML", reply_markup=markup)

def get_user_consent(user_id):
    return user_id in user_consents

# Admin Premium Komutları
@bot.message_handler(commands=['pre'])
def add_premium_user(message):
    if message.from_user.id != BOT_OWNER_ID:
        bot.reply_to(message, "⛔ Bu komutu sadece bot sahibi kullanabilir.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Kullanım: /pre <user_id> [gün_sayısı]\nÖrnek: /pre 123456789 30")
            return
        
        user_id = int(parts[1])
        days = 30
        if len(parts) >= 3:
            days = int(parts[2])
        
        premium_until = add_premium_user_to_files(user_id, days)
        
        # Kullanıcıya bildirim
        try:
            bot.send_message(user_id, f"🎉 **Tebrikler! Premium üyeliğiniz aktif edildi!**\n\n"
                                    f"⭐ **Premium Süresi:** {days} gün\n"
                                    f"📅 **Bitiş Tarihi:** {premium_until.strftime('%d/%m/%Y %H:%M')}\n\n"
                                    f"Artık tüm premium özelliklere erişebilirsiniz!")
        except:
            pass
        
        bot.reply_to(message, f"✅ **Premium üyelik başarıyla eklendi!**\n\n"
                            f"👤 **Kullanıcı ID:** {user_id}\n"
                            f"⭐ **Süre:** {days} gün\n"
                            f"📅 **Bitiş:** {premium_until.strftime('%d/%m/%Y %H:%M')}\n"
                            f"💾 **Kayıt:** TXT + JSON")
        
    except ValueError:
        bot.reply_to(message, "❌ Geçersiz user_id veya gün sayısı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['unpre'])
def remove_premium_user(message):
    if message.from_user.id != BOT_OWNER_ID:
        bot.reply_to(message, "⛔ Bu komutu sadece bot sahibi kullanabilir.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Kullanım: /unpre <user_id>\nÖrnek: /unpre 123456789")
            return
        
        user_id = int(parts[1])
        remove_premium_user_from_files(user_id)
        
        try:
            bot.send_message(user_id, "❌ **Premium üyeliğiniz sonlandırıldı!**\n\n"
                                    "Premium özelliklere erişiminiz kaldırıldı.")
        except:
            pass
        
        bot.reply_to(message, f"✅ **Premium üyelik kaldırıldı!**\n\n"
                            f"👤 **Kullanıcı ID:** {user_id}\n"
                            f"💾 **Kayıt:** TXT + JSON silindi")
        
    except ValueError:
        bot.reply_to(message, "❌ Geçersiz user_id.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['preinfo'])
def get_premium_info(message):
    if message.from_user.id != BOT_OWNER_ID:
        bot.reply_to(message, "⛔ Bu komutu sadece bot sahibi kullanabilir.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Kullanım: /preinfo <user_id>\nÖrnek: /preinfo 123456789")
            return
        
        user_id = int(parts[1])
        user_id_str = str(user_id)
        
        # JSON'dan bilgileri al
        try:
            with open("premium_users.json", "r") as file:
                premium_data = json.load(file)
            
            if user_id_str in premium_data:
                user_data = premium_data[user_id_str]
                premium_until = datetime.fromisoformat(user_data['premium_until'])
                now = datetime.now()
                remaining_days = (premium_until - now).days
                
                status = "✅ AKTİF" if remaining_days > 0 else "❌ SÜRESİ DOLMUŞ"
                
                info_text = f"👤 **Premium Kullanıcı Bilgisi**\n\n"
                info_text += f"🆔 **User ID:** {user_id}\n"
                info_text += f"📅 **Eklenme Tarihi:** {datetime.fromisoformat(user_data['added_date']).strftime('%d/%m/%Y %H:%M')}\n"
                info_text += f"⭐ **Premium Durumu:** {status}\n"
                info_text += f"⏰ **Bitiş Tarihi:** {premium_until.strftime('%d/%m/%Y %H:%M')}\n"
                info_text += f"📊 **Kalan Gün:** {remaining_days} gün\n"
                info_text += f"🔧 **Ekleyen:** {user_data.get('added_by', 'admin')}\n"
                info_text += f"💾 **Kaynak:** JSON"
                
                bot.reply_to(message, info_text, parse_mode="Markdown")
            else:
                bot.reply_to(message, f"❌ **Kullanıcı premium değil:** {user_id}")
                
        except:
            bot.reply_to(message, f"❌ **Kullanıcı bulunamadı:** {user_id}")
            
    except ValueError:
        bot.reply_to(message, "❌ Geçersiz user_id.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['prelist'])
def send_premium_list(message):
    if message.from_user.id != BOT_OWNER_ID:
        bot.reply_to(message, "⛔ Bu komutu sadece bot sahibi kullanabilir.")
        return
    
    try:
        # TXT dosyasından listeyi al
        with open("premium_users.txt", "r") as file:
            premium_users = file.read().splitlines()
        
        # JSON'dan detaylı bilgileri al
        try:
            with open("premium_users.json", "r") as file:
                premium_data = json.load(file)
        except:
            premium_data = {}
        
        if premium_users:
            list_text = "📋 **Premium Üyeler Listesi**\n\n"
            
            for user_id in premium_users[:20]:
                if user_id in premium_data:
                    user_data = premium_data[user_id]
                    premium_until = datetime.fromisoformat(user_data['premium_until'])
                    remaining_days = (premium_until - datetime.now()).days
                    status = "✅" if remaining_days > 0 else "❌"
                    list_text += f"{status} {user_id} - {remaining_days}gün kalan\n"
                else:
                    list_text += f"⚠️ {user_id} - Sadece TXT'de\n"
            
            if len(premium_users) > 20:
                list_text += f"\n... ve {len(premium_users) - 20} kullanıcı daha"
            
            bot.reply_to(message, list_text, parse_mode="Markdown")
        else:
            bot.reply_to(message, "ℹ️ Henüz premium üye yok.")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# Ana Bot Fonksiyonları
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if user_id not in user_consents:
        language = user_languages.get(user_id, 'en')
        send_legal_warning(message.chat.id, language)
        return
    
    if user_id not in user_languages:
        user_languages[user_id] = 'en'
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
    ss7_button = types.InlineKeyboardButton(messages[language]['ss7_button'], callback_data="ss7_exploit")
    
    markup.add(settings_button, help_button)
    markup.add(premium_button)
    markup.add(ss7_button)
    
    bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode="HTML")

# Callback Handler'lar
@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def select_language(call):
    user_id = call.from_user.id
    selected_lang = call.data.split("_")[1]
    user_languages[user_id] = selected_lang

    language = user_languages[user_id]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_main_menu(call.message.chat.id, language)

@bot.callback_query_handler(func=lambda call: call.data == "legal_consent")
def handle_legal_consent(call):
    user_id = call.from_user.id
    user_consents[user_id] = {
        'consent_date': datetime.now().isoformat(),
        'ip_address': 'N/A'
    }
    
    bot.edit_message_text(
        "✅ <b>Yasal onay verildi. Tüm sorumluluk size aittir.</b>\n\nŞimdi dil seçimi yapın:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )
    
    language = user_languages.get(user_id, 'en')
    welcome_text = messages[language]['welcome_select']

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"))
    markup.add(types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    markup.add(types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"))
    markup.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi"))

    bot.send_message(call.message.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "ss7_exploit")
def handle_ss7_exploit(call):
    user_id = call.from_user.id
    language = user_languages.get(user_id, 'en')
    
    if not is_premium_user(user_id):
        bot.answer_callback_query(call.id, messages[language]['premium_warning'], show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(messages[language]['ss7_confirm'], callback_data="confirm_ss7"))
    markup.add(types.InlineKeyboardButton(messages[language]['ss7_cancel'], callback_data="cancel_ss7"))
    
    warning_text = f"""
🔴 <b>{messages[language]['ss7_warning']}</b>

⚠️ <b>BU ÖZELLİK İLE:</b>
• GSM ağ altyapısına erişim sağlanır
• IMSI ve konum bilgileri çekilir
• Abone verilerine erişilir

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
    
    user_states[user_id] = 'awaiting_ss7_number'

@bot.callback_query_handler(func=lambda call: call.data == "cancel_ss7")
def cancel_ss7_exploit(call):
    user_id = call.from_user.id
    language = user_languages.get(user_id, 'en')
    
    bot.edit_message_text(
        "❌ SS7 Exploit iptal edildi.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )
    user_states[user_id] = None

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_ss7_number')
def handle_ss7_number(message):
    user_id = message.from_user.id
    phone_number = message.text
    language = user_languages.get(user_id, 'en')
    
    bot.send_message(message.chat.id, "🛰️ <b>SS7 Exploit Çalıştırılıyor...</b>", parse_mode="HTML")
    
    gsm_exploiter = GSMNetworkExploiter()
    network_data = gsm_exploiter.get_network_data(phone_number)
    
    report_text = f"""
🛰️ <b>SS7 EXPLOIT RAPORU</b>

📞 <b>Hedef Numara:</b> {phone_number}
⏰ <b>Sorgu Zamanı:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

🔍 <b>IMSI Bilgileri:</b>
├ IMSI: {network_data['imsi_info']['imsi']}
├ Ülke Kodu: {network_data['imsi_info']['country_code']}
├ Ağ Kodu: {network_data['imsi_info']['network_code']}
└ Abone ID: {network_data['imsi_info']['subscriber_id']}

📍 <b>Konum Bilgisi:</b>
├ Enlem: {network_data['location_info']['coordinates']['latitude']}
├ Boylam: {network_data['location_info']['coordinates']['longitude']}
├ Doğruluk: {network_data['location_info']['coordinates']['range']}m
├ LAC: {network_data['location_info']['cell_location']['lac']}
└ Cell ID: {network_data['location_info']['cell_location']['cell_id']}

📡 <b>Ağ Bilgisi:</b>
├ Operatör: {network_data['network_info']['operator']}
├ MCC: {network_data['network_info']['mcc']}
├ MNC: {network_data['network_info']['mnc']}
└ Teknoloji: {network_data['network_info']['technology']}

👤 <b>Abone Bilgisi:</b>
├ Durum: {network_data['subscriber_info']['status']}
├ Hat Türü: {network_data['subscriber_info']['line_type']}
├ Aktivasyon: {network_data['subscriber_info']['activation_date']}
└ Bakiye: {network_data['subscriber_info']['balance']}

⚠️ <i>Bu veriler simülasyon amaçlıdır.</i>
"""
    
    bot.send_message(message.chat.id, report_text, parse_mode="HTML")
    user_states[user_id] = None

# GÜNCELLENMİŞ FORMAT FONKSİYONU
def format_enhanced_response(result, language, is_premium):
    basic = result['basic_info']
    premium = result['premium_info']
    
    response = f"{messages[language]['phone_info']}\n"
    response += f"    ├🌍 <b>{messages[language]['country']}:</b> {basic['country']}\n"
    response += f"    ├📶 <b>{messages[language]['operator']}:</b> {basic['operator']}\n"
    response += f"    ├⏰ <b>{messages[language]['timezones']}:</b> {basic['timezones']}\n"
    response += f"    ├🔢 <b>{messages[language]['number_type']}:</b> {basic['number_type']}\n"
    response += f"    ├✅ <b>{messages[language]['valid_number']}:</b> {basic['valid_number']}\n"
    response += f"    ├📍 <b>{messages[language]['national_number']}:</b> {basic['national_number']}\n"
    response += f"    ├🗺 <b>{messages[language]['area_code']}:</b> {basic['area_code']}\n"
    response += f"    └📞 <b>{messages[language]['e164_format']}:</b> {basic['e164_format']}\n\n"
    
    if is_premium and premium:
        response += f"{messages[language]['person_info']}\n"
        response += f"    ├🔓 <b>{messages[language]['name']}:</b> {premium['person_info']['name']}\n"
        response += f"    ├🔓 <b>{messages[language]['surname']}:</b> {premium['person_info']['surname']}\n"
        response += f"    ├🔓 <b>{messages[language]['birthplace']}:</b> {premium['person_info']['birthplace']}\n"
        response += f"    ├🔓 <b>{messages[language]['birth_date']}:</b> {premium['person_info']['birth_date']}\n"
        response += f"    ├🔓 <b>{messages[language]['age']}:</b> {premium['person_info']['age']}\n"
        
        # Premium butonları
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("👤 Detaylı Kişi Bilgileri", callback_data=f"details_{result['query_id']}"),
            types.InlineKeyboardButton("📍 Canlı Konum", callback_data=f"location_{result['query_id']}")
        )
        markup.add(types.InlineKeyboardButton("🛰️ SS7 Exploit", callback_data="ss7_exploit"))
        
    else:
        response += f"{messages[language]['person_info']}\n"
        response += f"    ├🔒 <b>{messages[language]['name']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
        response += f"    ├🔒 <b>{messages[language]['surname']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
        response += f"    ├🔒 <b>{messages[language]['birthplace']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
        response += f"    ├🔒 <b>{messages[language]['birth_date']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
        response += f"    ├🔒 <b>{messages[language]['age']}:</b> <span class='tg-spoiler'>{messages[language]['premium_required']}</span>\n"
        
        # Premium satın alma butonu
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(messages[language]['premium_button'], callback_data="buy_premium"))
        
        response += f"\n{messages[language]['live_location_warning']}"
    
    return response, markup

# GÜNCELLENMİŞ MESAJ HANDLER
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    language = user_languages.get(user_id, 'en')
    
    if not get_user_consent(user_id):
        send_legal_warning(message.chat.id, language)
        return
    
    phone_number_text = message.text
    
    if user_states.get(user_id) == 'awaiting_ss7_number':
        handle_ss7_number(message)
        return
    
    result = enhanced_phone_query(phone_number_text, user_id)
    
    if result:
        response, markup = format_enhanced_response(result, language, is_premium_user(user_id))
        bot.reply_to(message, response, parse_mode="HTML", reply_markup=markup)
    else:
        bot.reply_to(message, messages[language]['invalid_number'])

@bot.callback_query_handler(func=lambda call: call.data == "buy_premium")
def buy_premium(call):
    user_id = call.from_user.id
    language = user_languages.get(user_id, 'en')

    title = messages[language]['purchase_title']
    description = messages[language]['purchase_description']
    price = 1
    prices = [LabeledPrice(label=title, amount=price * 1000)]

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
    
    # Sadece dosyalara kaydet
    premium_until = add_premium_user_to_files(user_id, 30)
    
    success_message = f"✅ {messages[language]['successful_payment']}\n"
    success_message += f"⭐ **Premium Süresi:** 30 gün\n"
    success_message += f"📅 **Bitiş Tarihi:** {premium_until.strftime('%d/%m/%Y %H:%M')}"
    
    bot.send_message(user_id, success_message, parse_mode="Markdown")

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
    show_main_menu(call.message.chat.id, language)

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
            'number_type': str(phonenumbers.number_type(phone_number)),
            'valid_number': phonenumbers.is_valid_number(phone_number),
            'national_number': phonenumbers.national_significant_number(phone_number),
            'area_code': phonenumbers.region_code_for_number(phone_number),
            'e164_format': phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
        }
        return details

    except NumberParseException:
        return None

# Logo ve başlatma
logo2 = '''
88  dP 88 88b 88  dP""b8      dP"Yb  8888b.  88 88b 88
88odP  88 88Yb88 dP   `"     dP   Yb  8I  Yb 88 88Yb88
88"Yb  88 88 Y88 Yb  "88     Yb   dP  8I  dY 88 88 Y88
88  Yb 88 88  Y8  YboodP      YbodP  8888Y"  88 88  Y8
'''

print('bot çalışıyor')

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





