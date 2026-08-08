from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, WebAppInfo
from config import MSG_EFFECT, OWNER_ID, WEBAPP_URL, INDEX_URL
from helper.pyro_listen import ListenerTimeout
from helper.helper_func import styled_button, safe_edit_text

#===============================================================#

@Client.on_message(filters.command('db') & filters.private)
async def db_channels_command(client: Client, message: Message):
    """Direct command to manage DB channels"""
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    # Show current DB channels status
    db_channels = getattr(client, 'db_channels', {})
    primary_db = getattr(client, 'primary_db_channel', client.db)
    
    if db_channels:
        channel_list = []
        for channel_id_str, channel_data in db_channels.items():
            channel_name = channel_data.get('name', 'ᴜɴᴋɴᴏᴡɴ')
            is_primary = "✓ ᴘʀɪᴍᴀʀʏ" if channel_data.get('is_primary', False) else "• sᴇᴄᴏɴᴅᴀʀʏ"
            is_active = "✓ ᴀᴄᴛɪᴠᴇ" if channel_data.get('is_active', True) else "✗ ɪɴᴀᴄᴛɪᴠᴇ"
            channel_list.append(f"• `{channel_name}` (`{channel_id_str}`)\n  {is_primary} | {is_active}")
        
        channels_display = "\n\n".join(channel_list)
    else:
        channels_display = "_ɴᴏ ᴀᴅᴅɪᴛɪᴏɴᴀʟ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ᴄᴏɴғɪɢᴜʀᴇᴅ_"
    
    msg = f"""<blockquote>✦ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ᴍᴀɴᴀɢᴇᴍᴇɴᴛ</blockquote>

›› **ᴄᴜʀʀᴇɴᴛ ᴘʀɪᴍᴀʀʏ ᴅʙ:** `{primary_db}`
›› **ᴛᴏᴛᴀʟ ᴅʙ ᴄʜᴀɴɴᴇʟs:** `{len(db_channels)}`

**ᴄᴏɴғɪɢᴜʀᴇᴅ ᴄʜᴀɴɴᴇʟs:**
{channels_display}

__ᴜsᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs!__
"""
    
    reply_markup = InlineKeyboardMarkup([
        [styled_button('›› ᴀᴅᴅ ᴅʙ ᴄʜᴀɴɴᴇʟ', style="primary", callback_data='add_db_channel')],
        [styled_button('›› ʀᴇᴍᴏᴠᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ', style="primary", callback_data='rm_db_channel')],
        [styled_button('›› sᴇᴛ ᴘʀɪᴍᴀʀʏ', style="primary", callback_data='set_primary_db')],
        [styled_button('›› ᴛᴏɢɢʟᴇ sᴛᴀᴛᴜs', style="primary", callback_data='toggle_db_status')],
        [styled_button('›› ᴠɪᴇᴡ ᴅᴇᴛᴀɪʟs', style="primary", callback_data='db_details')]
    ])
    
    await message.reply(msg, reply_markup=reply_markup)

#===============================================================#
# NOTE: Callback handlers for add_db_channel, rm_db_channel, set_primary_db, and toggle_db_status
# are implemented in settings.py to avoid conflicts. Only direct commands are handled here.
#===============================================================#

@Client.on_callback_query(filters.regex("^db_details$"))
async def db_details(client, query):
    """Show detailed information about DB channels"""
    if not query.from_user.id in client.admins:
        return await query.answer('✗ ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs!', show_alert=True)
    
    await query.answer()
    
    db_channels = getattr(client, 'db_channels', {})
    primary_db = getattr(client, 'primary_db_channel', client.db)
    
    msg = f"""<blockquote>✦ ᴅᴇᴛᴀɪʟᴇᴅ ᴅʙ ᴄʜᴀɴɴᴇʟs ɪɴғᴏʀᴍᴀᴛɪᴏɴ</blockquote>

›› **ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ:** `{primary_db}`
›› **ᴛᴏᴛᴀʟ ᴄᴏɴғɪɢᴜʀᴇᴅ:** `{len(db_channels)}`

"""
    
    if db_channels:
        for i, (channel_id_str, channel_data) in enumerate(db_channels.items(), 1):
            channel_name = channel_data.get('name', 'ᴜɴᴋɴᴏᴡɴ')
            is_primary = channel_data.get('is_primary', False)
            is_active = channel_data.get('is_active', True)
            added_by = channel_data.get('added_by', 'ᴜɴᴋɴᴏᴡɴ')
            
            status_emoji = "✓" if is_primary else "•"
            active_emoji = "✓" if is_active else "✗"
            
            msg += f"""**{i}. {channel_name}**
• **ɪᴅ:** `{channel_id_str}`
• **sᴛᴀᴛᴜs:** {status_emoji} {'ᴘʀɪᴍᴀʀʏ' if is_primary else 'sᴇᴄᴏɴᴅᴀʀʏ'}
• **ᴀᴄᴛɪᴠᴇ:** {active_emoji} {'ʏᴇs' if is_active else 'ɴᴏ'}
• **ᴀᴅᴅᴇᴅ ʙʏ:** `{added_by}`

"""
    else:
        msg += "_ɴᴏ ᴀᴅᴅɪᴛɪᴏɴᴀʟ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ᴄᴏɴғɪɢᴜʀᴇᴅ_\n\n"
    
    msg += """**✦ ɴᴏᴛᴇs:**
• ᴘʀɪᴍᴀʀʏ ᴄʜᴀɴɴᴇʟ ɪs ᴜsᴇᴅ ғɪʀsᴛ ғᴏʀ ʀᴇᴛʀɪᴇᴠɪɴɢ ғɪʟᴇs
• sᴇᴄᴏɴᴅᴀʀʏ ᴄʜᴀɴɴᴇʟs ᴀʀᴇ ᴜsᴇᴅ ᴀs ғᴀʟʟʙᴀᴄᴋ
• ɪɴᴀᴄᴛɪᴠᴇ ᴄʜᴀɴɴᴇʟs ᴀʀᴇ sᴋɪᴘᴘᴇᴅ ᴅᴜʀɪɴɢ ғɪʟᴇ ʀᴇᴛʀɪᴇᴠᴀʟ
• ʏᴏᴜ ᴄᴀɴ ʜᴀᴠᴇ ᴍᴜʟᴛɪᴘʟᴇ ᴅʙ ᴄʜᴀɴɴᴇʟs ғᴏʀ ʙᴇᴛᴛᴇʀ ʀᴇʟɪᴀʙɪʟɪᴛʏ"""
    
    reply_markup = InlineKeyboardMarkup([
        [styled_button('‹ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ', style="primary", callback_data='back_to_db_management')]
    ])
    
    await safe_edit_text(query.message, msg, reply_markup=reply_markup)

#===============================================================#

@Client.on_callback_query(filters.regex("^back_to_db_management$"))
async def back_to_db_management(client, query):
    """Go back to main DB channels management"""
    if not query.from_user.id in client.admins:
        return await query.answer('✗ ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs!', show_alert=True)
    
    await query.answer()
    
    # Redirect to main dbchannels display
    db_channels = getattr(client, 'db_channels', {})
    primary_db = getattr(client, 'primary_db_channel', client.db)
    
    if db_channels:
        channel_list = []
        for channel_id_str, channel_data in db_channels.items():
            channel_name = channel_data.get('name', 'ᴜɴᴋɴᴏᴡɴ')
            is_primary = "✓ ᴘʀɪᴍᴀʀʏ" if channel_data.get('is_primary', False) else "• sᴇᴄᴏɴᴅᴀʀʏ"
            is_active = "✓ ᴀᴄᴛɪᴠᴇ" if channel_data.get('is_active', True) else "✗ ɪɴᴀᴄᴛɪᴠᴇ"
            channel_list.append(f"• `{channel_name}` (`{channel_id_str}`)\n  {is_primary} | {is_active}")
        
        channels_display = "\n\n".join(channel_list)
    else:
        channels_display = "_ɴᴏ ᴀᴅᴅɪᴛɪᴏɴᴀʟ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ᴄᴏɴғɪɢᴜʀᴇᴅ_"
    
    msg = f"""<blockquote>✦ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ᴍᴀɴᴀɢᴇᴍᴇɴᴛ</blockquote>

›› **ᴄᴜʀʀᴇɴᴛ ᴘʀɪᴍᴀʀʏ ᴅʙ:** `{primary_db}`
›› **ᴛᴏᴛᴀʟ ᴅʙ ᴄʜᴀɴɴᴇʟs:** `{len(db_channels)}`

**ᴄᴏɴғɪɢᴜʀᴇᴅ ᴄʜᴀɴɴᴇʟs:**
{channels_display}

__ᴜsᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs!__
"""
    
    reply_markup = InlineKeyboardMarkup([
        [styled_button('›› ᴀᴅᴅ ᴅʙ ᴄʜᴀɴɴᴇʟ', style="primary", callback_data='add_db_channel')],
        [styled_button('›› ʀᴇᴍᴏᴠᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ', style="primary", callback_data='rm_db_channel')],
        [styled_button('›› sᴇᴛ ᴘʀɪᴍᴀʀʏ', style="primary", callback_data='set_primary_db')],
        [styled_button('›› ᴛᴏɢɢʟᴇ sᴛᴀᴛᴜs', style="primary", callback_data='toggle_db_status')],
        [styled_button('›› ᴠɪᴇᴡ ᴅᴇᴛᴀɪʟs', style="primary", callback_data='db_details')]
    ])
    
    
    await safe_edit_text(query.message, msg, reply_markup=reply_markup)

#===============================================================#

@Client.on_message(filters.command(['adddb', 'add_db']) & filters.private)
async def quick_add_db(client: Client, message: Message):
    """Quick command to add a DB channel"""
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    # Check if channel ID is provided in the command
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("""<blockquote>✦ ᴀᴅᴅ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ</blockquote>

›› **ᴜsᴀɢᴇ:** `/adddb <channel_id>`
›› **ᴇxᴀᴍᴘʟᴇ:** `/adddb -1001234567890`

**ɴᴏᴛᴇ:** ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ!""")
    
    try:
        channel_id = int(args[1])
    except ValueError:
        return await message.reply("**✗ ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ! ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ɴᴇɢᴀᴛɪᴠᴇ ɪɴᴛᴇɢᴇʀ.**")
    
    # Check if channel already exists
    db_channels = getattr(client, 'db_channels', {})
    if str(channel_id) in db_channels:
        return await message.reply(f"**✗ ᴄʜᴀɴɴᴇʟ `{channel_id}` ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ ᴀs ᴀ ᴅʙ ᴄʜᴀɴɴᴇʟ!**")
    
    # Verify bot can access the channel
    try:
        chat = await client.get_chat(channel_id)
        test_msg = await client.send_message(chat_id=channel_id, text="ᴛᴇsᴛɪɴɢ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴀᴄᴄᴇss - @Okabe_xRintarou")
        await test_msg.delete()
        
        # Add channel to database
        channel_data = {
            'name': chat.title,
            'is_primary': len(db_channels) == 0,  # First channel becomes primary
            'is_active': True,
            'added_by': message.from_user.id
        }
        
        await client.mongodb.add_db_channel(channel_id, channel_data)
        
        # Update client attributes
        if not hasattr(client, 'db_channels'):
            client.db_channels = {}
        client.db_channels[str(channel_id)] = channel_data
        
        # Set as primary if it's the first channel
        if channel_data['is_primary']:
            client.primary_db_channel = channel_id
            await client.mongodb.set_primary_db_channel(channel_id)
        
        await message.reply(f"""**✓ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**

›› **ᴄʜᴀɴɴᴇʟ:** `{chat.title}`
›› **ɪᴅ:** `{channel_id}`
›› **sᴛᴀᴛᴜs:** {'ᴘʀɪᴍᴀʀʏ' if channel_data['is_primary'] else 'sᴇᴄᴏɴᴅᴀʀʏ'}

ᴜsᴇ `/dbchannels` ᴛᴏ ᴍᴀɴᴀɢᴇ ᴀʟʟ ʏᴏᴜʀ ᴅʙ ᴄʜᴀɴɴᴇʟs.""")
    
    except Exception as e:
        await message.reply(f"""**✗ ᴇʀʀᴏʀ ᴀᴄᴄᴇssɪɴɢ ᴄʜᴀɴɴᴇʟ!**

›› **ᴇʀʀᴏʀ:** `{str(e)}`

**ᴘʟᴇᴀsᴇ ᴍᴀᴋᴇ sᴜʀᴇ:**
• ʙᴏᴛ ɪs ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ
• ᴄʜᴀɴɴᴇʟ ɪᴅ ɪs ᴄᴏʀʀᴇᴄᴛ
• ᴄʜᴀɴɴᴇʟ ᴇxɪsᴛs""")

#===============================================================#

@Client.on_message(filters.command(['removedb', 'rm_db']) & filters.private)
async def quick_remove_db(client: Client, message: Message):
    """Quick command to remove a DB channel"""
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    # Check if channel ID is provided in the command
    args = message.text.split()
    if len(args) < 2:
        db_channels = getattr(client, 'db_channels', {})
        if not db_channels:
            return await message.reply("**✗ ɴᴏ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ᴛᴏ ʀᴇᴍᴏᴠᴇ!**")
        
        msg = """<blockquote>✦ ʀᴇᴍᴏᴠᴇ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ</blockquote>

›› **ᴜsᴀɢᴇ:** `/removedb <channel_id>`

**ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʜᴀɴɴᴇʟs:**
"""
        for channel_id_str, channel_data in db_channels.items():
            channel_name = channel_data.get('name', 'ᴜɴᴋɴᴏᴡɴ')
            is_primary = " (ᴘʀɪᴍᴀʀʏ)" if channel_data.get('is_primary', False) else ""
            msg += f"• `{channel_name}` - `{channel_id_str}`{is_primary}\n"
        
        return await message.reply(msg)
    
    try:
        channel_id = int(args[1])
    except ValueError:
        return await message.reply("**✗ ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ! ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ɴᴇɢᴀᴛɪᴠᴇ ɪɴᴛᴇɢᴇʀ.**")
    
    db_channels = getattr(client, 'db_channels', {})
    
    if str(channel_id) not in db_channels:
        return await message.reply(f"**✗ ᴄʜᴀɴɴᴇʟ `{channel_id}` ɪs ɴᴏᴛ ɪɴ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟs ʟɪsᴛ!**")
    
    # Check if trying to remove primary channel
    if db_channels[str(channel_id)].get('is_primary', False) and len(db_channels) > 1:
        return await message.reply("**✗ ᴄᴀɴɴᴏᴛ ʀᴇᴍᴏᴠᴇ ᴘʀɪᴍᴀʀʏ ᴄʜᴀɴɴᴇʟ!**\n\n__ᴘʟᴇᴀsᴇ sᴇᴛ ᴀɴᴏᴛʜᴇʀ ᴄʜᴀɴɴᴇʟ ᴀs ᴘʀɪᴍᴀʀʏ ғɪʀsᴛ ᴜsɪɴɢ `/dbchannels`.__")
    
    # Remove from database and client
    channel_name = db_channels[str(channel_id)].get('name', 'ᴜɴᴋɴᴏᴡɴ')
    await client.mongodb.remove_db_channel(channel_id)
    del client.db_channels[str(channel_id)]
    
    await message.reply(f"""**✓ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ ʀᴇᴍᴏᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**

›› **ʀᴇᴍᴏᴠᴇᴅ:** `{channel_name}` (`{channel_id}`)

ᴜsᴇ `/db` ᴛᴏ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ʀᴇᴍᴀɪɴɪɴɢ ᴅʙ ᴄʜᴀɴɴᴇʟs.""")

#===============================================================#

#==========================================================================#        

@Client.on_callback_query(filters.regex('^home$'))
async def home(client: Client, query: CallbackQuery):
    try:
        await query.answer()
    except Exception:
        pass
    buttons = []
    index_url = (INDEX_URL or WEBAPP_URL or "").strip()
    if index_url.startswith("https://"):
        buttons.append([styled_button("ᴏᴘᴇɴ ɪɴᴅᴇx", style="success", web_app=WebAppInfo(url=index_url))])
    elif index_url.startswith("http://"):
        buttons.append([styled_button("ᴏᴘᴇɴ ɪɴᴅᴇx", style="success", url=index_url)])
    buttons.append([styled_button("Help", style="danger", callback_data="about"), styled_button("Close", style="danger", callback_data="close")])
    if query.from_user.id in client.admins:
        buttons.insert(0, [styled_button("⛩️ ꜱᴇᴛᴛɪɴɢꜱ ⛩️", style="danger", callback_data="settings")])
    text = client.messages.get('START', 'No Start Message').format(
        first=query.from_user.first_name,
        last=query.from_user.last_name,
        username=None if not query.from_user.username else '@' + query.from_user.username,
        mention=query.from_user.mention,
        id=query.from_user.id,
    )
    await safe_edit_text(query.message, text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex('^about$'))
async def about(client: Client, query: CallbackQuery):
    try:
        await query.answer()
    except Exception:
        pass
    buttons = [[styled_button("Back", style="danger", callback_data="home"), styled_button("Close", style="danger", callback_data="close")]]
    text = client.messages.get('ABOUT', 'No Start Message').format(
        owner_id=client.owner,
        bot_username=client.username,
        first=query.from_user.first_name,
        last=query.from_user.last_name,
        username=None if not query.from_user.username else '@' + query.from_user.username,
        mention=query.from_user.mention,
        id=query.from_user.id,
    )
    await safe_edit_text(query.message, text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex('^close$'))
async def close(client: Client, query: CallbackQuery):
    try:
        await query.answer()
    except Exception:
        pass
    try:
        await query.message.delete()
    except Exception:
        pass
    try:
        if query.message.reply_to_message:
            await query.message.reply_to_message.delete()
    except Exception:
        pass

#==========================================================================#        

@Client.on_message(filters.command('ban'))
async def ban(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    try:
        user_ids = message.text.split(maxsplit=1)[1]
        c = 0
        for user_id in user_ids.split():
            user_id = int(user_id)
            c = c + 1
            if user_id in client.admins:
                continue
            if not await client.mongodb.present_user(user_id):
                await client.mongodb.add_user(user_id, True)
                continue
            else:
                await client.mongodb.ban_user(user_id)
        return await message.reply(f"__{c} users have been banned!__")
    except Exception as e:
    
        return await message.reply(f"**Error:** `{e}`")

#==========================================================================#        

@Client.on_message(filters.command('unban'))
async def unban(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    try:
        user_ids = message.text.split(maxsplit=1)[1]
        c = 0
        for user_id in user_ids.split():
            user_id = int(user_id)
            c = c + 1
            if user_id in client.admins:
                continue
            if not await client.mongodb.present_user(user_id):
                await client.mongodb.add_user(user_id)
                continue
            else:
                await client.mongodb.unban_user(user_id)
        return await message.reply(f"__{c} users have been unbanned!__")
    except Exception as e:
    
        return await message.reply(f"**Error:** `{e}`")

#==========================================================================#

# ---------------------------------------------------------------------------
# /commands — owner only: list every bot command
# ---------------------------------------------------------------------------

@Client.on_message(filters.command("commands") & filters.private)
async def list_all_commands(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else 0
    if uid != OWNER_ID:
        return
    text = """<b>📋 Bot Commands</b>

<b>User</b>
├ /start — Start the bot
├ /anidex — Open Anime Index
├ /profile — Your profile
├ /request — Request something
└ (send anime title) — Search library

<b>Links</b>
├ /genlink — Generate file link
└ /batch — Batch file links

<b>Admin</b>
├ /stats — Bot stats
├ /users — User count
├ /broadcast — Broadcast message
├ /pbroadcast — Premium broadcast
├ /shortner — Shortener panel
├ /db — DB channels
├ /adddb — Add DB channel
├ /removedb — Remove DB channel
├ /ban — Ban user
├ /unban — Unban user
├ /addpremium — Add premium
├ /delpremium — Remove premium
├ /premiumusers — List premium
└ /commands — This list (owner only)"""
    await message.reply_text(text)
