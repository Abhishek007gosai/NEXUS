from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.pyromod import ListenerTimeout
from config import OWNER_ID
import humanize

#===============================================================#

@Client.on_callback_query(filters.regex("^settings$"))
async def settings(client, query):
    # Count active force subscription channels by type
    total_fsub = len(client.fsub_dict)
    request_enabled = sum(1 for data in client.fsub_dict.values() if data[2])
    timer_enabled = sum(1 for data in client.fsub_dict.values() if data[3] > 0)
    
    # Count DB channels
    total_db_channels = len(getattr(client, 'db_channels', {}))
    primary_db = getattr(client, 'primary_db_channel', client.db)
    
    msg = f"""<blockquote>✦ sᴇᴛᴛɪɴɢs ᴏғ @{client.username}</blockquote>
›› **ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟs:** `{total_fsub}` (ʀᴇǫᴜᴇsᴛ: {request_enabled}, ᴛɪᴍᴇʀ: {timer_enabled})
›› **ᴅʙ ᴄʜᴀɴɴᴇʟs:** `{total_db_channels}` (ᴘʀɪᴍᴀʀʏ: `{primary_db}`)
›› **ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ:** `{client.auto_del}`
›› **ᴘʀᴏᴛᴇᴄᴛ ᴄᴏɴᴛᴇɴᴛ:** `{"✓ ᴛʀᴜᴇ" if client.protect else "✗ ꜰᴀʟsᴇ"}`
›› **ᴅɪsᴀʙʟᴇ ʙᴜᴛᴛᴏɴ:** `{"✓ ᴛʀᴜᴇ" if client.disable_btn else "✗ ꜰᴀʟsᴇ"}`
›› **ʀᴇᴘʟʏ ᴛᴇxᴛ:** `{client.reply_text if client.reply_text else 'ɴᴏɴᴇ'}`
›› **ᴀᴅᴍɪɴs:** `{len(client.admins)}`
›› **sʜᴏʀᴛɴᴇʀ ᴜʀʟ:** `{getattr(client, 'short_url', 'ɴᴏᴛ sᴇᴛ')}`
›› **ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ:** `{getattr(client, 'tutorial_link', 'ɴᴏᴛ sᴇᴛ')}`
›› **sᴛᴀʀᴛ ɪᴍᴀɢᴇ:** `{bool(client.messages.get('START_PHOTO', ''))}`
›› **ꜰᴏʀᴄᴇ sᴜʙ ɪᴍᴀɢᴇ:** `{bool(client.messages.get('FSUB_PHOTO', ''))}`
    """
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('🔵 ʟɪɴᴋ sʜᴀʀᴇ ᴍᴇɴᴜ', 'link_share'), InlineKeyboardButton('🔵 ꜰsᴜʙ ᴄʜᴀɴɴᴇʟs', 'fsub')],
        [InlineKeyboardButton('🔵 ᴅʙ ᴄʜᴀɴɴᴇʟs', 'db_channels'), InlineKeyboardButton('🔵 ᴄᴀᴘᴛɪᴏɴ', 'custom_caption')],
        [InlineKeyboardButton('🔵 ᴀᴅᴍɪɴꜱ', 'admins'), InlineKeyboardButton('🔵 ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ', 'auto_del')],
        [InlineKeyboardButton('🔵 ʜᴏᴍᴇ', 'home'), InlineKeyboardButton('🔵 ›› ɴᴇxᴛ', 'settings_page_2')]
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

#===============================================================#

@Client.on_callback_query(filters.regex("^settings_page_2$"))
async def settings_page_2(client, query):
    # Count active force subscription channels by type
    total_fsub = len(client.fsub_dict)
    request_enabled = sum(1 for data in client.fsub_dict.values() if data[2])
    timer_enabled = sum(1 for data in client.fsub_dict.values() if data[3] > 0)
    
    # Count DB channels
    total_db_channels = len(getattr(client, 'db_channels', {}))
    primary_db = getattr(client, 'primary_db_channel', client.db)
    
    msg = f"""<blockquote>✦ sᴇᴛᴛɪɴɢs ᴏғ @{client.username}</blockquote>
›› **ꜰsᴜʙ ᴄʜᴀɴɴᴇʟs:** `{total_fsub}` (ʀᴇǫᴜᴇsᴛ: {request_enabled}, ᴛɪᴍᴇʀ: {timer_enabled})
›› **ᴅʙ ᴄʜᴀɴɴᴇʟs:** `{total_db_channels}` (ᴘʀɪᴍᴀʀʏ: `{primary_db}`)
›› **ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ:** `{client.auto_del}`
›› **ᴘʀᴏᴛᴇᴄᴛ ᴄᴏɴᴛᴇɴᴛ:** `{"✓ ᴛʀᴜᴇ" if client.protect else "✗ ꜰᴀʟsᴇ"}`
›› **ᴅɪsᴀʙʟᴇ ʙᴜᴛᴛᴏɴ:** `{"✓ ᴛʀᴜᴇ" if client.disable_btn else "✗ ꜰᴀʟsᴇ"}`
›› **ʀᴇᴘʟʏ ᴛᴇxᴛ:** `{client.reply_text if client.reply_text else 'ɴᴏɴᴇ'}`
›› **ᴀᴅᴍɪɴs:** `{len(client.admins)}`
›› **sʜᴏʀᴛɴᴇʀ ᴜʀʟ:** `{getattr(client, 'short_url', 'ɴᴏᴛ sᴇᴛ')}`
›› **ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ:** `{getattr(client, 'tutorial_link', 'ɴᴏᴛ sᴇᴛ')}`
›› **sᴛᴀʀᴛ ɪᴍᴀɢᴇ:** `{bool(client.messages.get('START_PHOTO', ''))}`
›› **ꜰᴏʀᴄᴇ sᴜʙ ɪᴍᴀɢᴇ:** `{bool(client.messages.get('FSUB_PHOTO', ''))}`
    """
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(f'ᴘʀᴏᴛᴇᴄᴛ ᴄᴏɴᴛᴇɴᴛ: {"🟢 ᴏɴ" if client.protect else "🔴 ᴏꜰꜰ"}', 'protect'), InlineKeyboardButton(f'ᴅɪsᴀʙʟᴇ ʙᴜᴛᴛᴏɴ: {"🟢 ᴏɴ" if client.disable_btn else "🔴 ᴏꜰꜰ"}', 'disable_btn')],
        [InlineKeyboardButton('🔵 ᴘʜᴏᴛᴏs', 'photos'), InlineKeyboardButton('🔵 ᴛᴇxᴛs', 'texts')],
        [InlineKeyboardButton('🔵 sʜᴏʀᴛɴᴇʀ', 'shortner')],
        [InlineKeyboardButton('🔴 ‹ ᴘʀᴇᴠ', 'settings'), InlineKeyboardButton('🟢 ʜᴏᴍᴇ', 'home')]
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

#===============================================================#

@Client.on_callback_query(filters.regex("^custom_caption$"))
async def custom_caption(client, query):
    if query.from_user.id not in client.admins:
        return await query.answer("✗ ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs!", show_alert=True)

    current = client.messages.get("CAPTION", "")
    current_display = current if current else "ɴᴏᴛ sᴇᴛ (ᴏʀɪɢɪɴᴀʟ ᴄᴀᴘᴛɪᴏɴ ᴡɪʟʟ ʙᴇ ᴜsᴇᴅ)"
    msg = f"""<blockquote>✦ ᴄᴜsᴛᴏᴍ ꜰɪʟᴇ ᴄᴀᴘᴛɪᴏɴ</blockquote>
›› **ᴄᴜʀʀᴇɴᴛ ᴄᴀᴘᴛɪᴏɴ:**
<pre>{current_display}</pre>

Send your new caption in the next 60 seconds.

Use <code>{{previouscaption}}</code> where you want the original file caption/name to appear.
Send <code>/remove</code> to disable the custom caption."""
    await query.answer()
    await query.message.edit_text(
        msg,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔴 ‹ ʙᴀᴄᴋ", "settings_page_2")]])
    )
    try:
        res = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        value = res.text.strip()
        if value.lower() == "/remove":
            value = ""
        await client.mongodb.update_message_setting("CAPTION", value)
        client.messages["CAPTION"] = value
        status = "disabled" if not value else "updated"
        await query.message.edit_text(
            f"<b>✓ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ {status} sᴜᴄᴄᴇssғᴜʟʟʏ.</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔴 ‹ ʙᴀᴄᴋ", "settings_page_2")]])
        )
    except ListenerTimeout:
        await query.message.edit_text(
            "<b>⌛ ᴛɪᴍᴇᴏᴜᴛ. ɴᴏ ᴄʜᴀɴɢᴇs ᴡᴇʀᴇ ᴍᴀᴅᴇ.</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔴 ‹ ʙᴀᴄᴋ", "settings_page_2")]])
        )

#===============================================================#

@Client.on_callback_query(filters.regex("^fsub$"))
async def fsub(client, query):
    # Create a formatted list of channels with names and IDs
    if client.fsub_dict:
        channel_list = []
        for channel_id, channel_data in client.fsub_dict.items():
            channel_name = channel_data[0] if channel_data and len(channel_data) > 0 else "Unknown"
            request_status = "✓ ʀᴇѦᴜᴇsᴛ" if channel_data[2] else "✗ ʀᴇѦᴜᴇsᴛ"
            timer_status = f"ᴛɪᴍᴇʀ: {channel_data[3]}ᴍ" if channel_data[3] > 0 else "ᴛɪᴍᴇʀ: ∞"
            channel_list.append(f"• `{channel_name}` (`{channel_id}`) - {request_status}, {timer_status}")
        
        channels_display = "\n".join(channel_list)
    else:
        channels_display = "_ɴᴏ ꜰᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴄʜᴀɴɴᴇʟs ᴄᴏɴғɪɢᴜʀᴇᴅ_"
    
    msg = f"""<blockquote>✦ ꜰᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ sᴇᴛᴛɪɴɢs</blockquote>
›› **ᴄᴏɴғɪɢᴜʀᴇᴅ ᴄʜᴀɴɴᴇʟs:**
{channels_display}

__ᴜsᴇ ᴛʜᴇ ᴀᴘᴘʀᴏᴘʀɪᴀᴛᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴀᴅᴅ ᴏʀ ʀᴇᴍᴏᴠᴇ ᴀ ꜰᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴄʜᴀɴɴᴇʟ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ɴᴇᴇᴅs!__
"""
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('🟢 ›› ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ', 'add_fsub'), InlineKeyboardButton('🔴 ›› ʀᴇᴍᴏᴠᴇ ᴄʜᴀɴɴᴇʟ', 'rm_fsub')],
        [InlineKeyboardButton('🔴 ‹ ʙᴀᴄᴋ', 'settings')]]
    )
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

#===============================================================#

@Client.on_callback_query(filters.regex("^db_channels$"))
async def db_channels(client, query):
    if not query.from_user.id in client.admins:
        return await query.answer('✗ ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs!', show_alert=True)
    
    # Create a formatted list of DB channels
    db_channels = getattr(client, 'db_channels', {})
    if db_channels:
        channel_list = []
        for channel_id_str, channel_data in db_channels.items():
            channel_name = channel_data.get('name', 'Unknown')
            is_primary = "✓ ᴘʀɪᴍᴀʀʏ" if channel_data.get('is_primary', False) else "• sᴇᴄᴏɴᴅᴀʀʏ"
            is_active = "✓ ᴀᴄᴛɪᴠᴇ" if channel_data.get('is_active', True) else "✗ ɪɴᴀᴄᴛɪᴠᴇ"
            channel_list.append(f"• `{channel_name}` (`{channel_id_str}`)\n  {is_primary} | {is_active}")
        
        channels_display = "\n\n".join(channel_list)
    else:
        channels_display = "_ɴᴏ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ᴄᴏɴғɪɢᴜʀᴇᴅ_"
    
    # Show current primary DB channel
    primary_db = getattr(client, 'primary_db_channel', client.db)
    
    msg = f"""<blockquote>✦ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs sᴇᴛᴛɪɴɢs</blockquote>
›› **ᴄᴜʀʀᴇɴᴛ ᴘʀɪᴍᴀʀʏ ᴅʙ:** `{primary_db}`
›› **ᴛᴏᴛᴀʟ ᴅʙ ᴄʜᴀɴɴᴇʟs:** `{len(db_channels)}`

**ᴄᴏɴғɪɢᴜʀᴇᴅ ᴄʜᴀɴɴᴇʟs:**
{channels_display}

__ᴜsᴇ ᴛʜᴇ ᴀᴘᴘʀᴏᴘʀɪᴀᴛᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs!__
"""
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('🟢 ›› ᴀᴅᴅ ᴅʙ ᴄʜᴀɴɴᴇʟ', 'add_db_channel'), InlineKeyboardButton('🔴 ›› ʀᴇᴍᴏᴠᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ', 'rm_db_channel')],
        [InlineKeyboardButton('🔵 ›› sᴇᴛ ᴘʀɪᴍᴀʀʏ', 'set_primary_db'), InlineKeyboardButton('🔵 ›› sᴛᴀᴛᴜs', 'toggle_db_status')],
        [InlineKeyboardButton('🔴 ‹ ʙᴀᴄᴋ', 'settings')]
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

#===============================================================#

@Client.on_callback_query(filters.regex("^add_db_channel$"))
async def add_db_channel(client, query):
    if not query.from_user.id in client.admins:
        return await query.answer('✗ ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs!', show_alert=True)
    
    await query.answer()
    msg = f"""<blockquote>✦ ᴀᴅᴅ ɴᴇᴡ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ</blockquote>
›› **ᴄᴜʀʀᴇɴᴛ ᴅʙ ᴄʜᴀɴɴᴇʟs:** `{len(getattr(client, 'db_channels', {}))}`

__sᴇɴᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ɪᴅ (ɴᴇɢᴀᴛɪᴠᴇ ɪɴᴛᴇɢᴇʀ ᴠᴀʟᴜᴇ) ᴏғ ᴛʜᴇ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴀᴅᴅ ɪɴ ᴛʜᴇ ɴᴇxᴛ 60 sᴇᴄᴏɴᴅs!__

**ᴇxᴀᴍᴘʟᴇ:** `-1001234567675`
**ɴᴏᴛᴇ:** ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ!"""
    
    await query.message.edit_text(msg)
    try:
        res = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        channel_id_text = res.text.strip()
        
        if not channel_id_text.lstrip('-').isdigit():
            return await query.message.edit_text("**✗ ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ! ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ɴᴇɢᴀᴛɪᴠᴇ ɪɴᴛᴇɢᴇʀ.**", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ‹ ʙᴀᴄᴋ', 'db_channels')]]))
        
        channel_id = int(channel_id_text)
        
        # Check if channel already exists
        db_channels = getattr(client, 'db_channels', {})
        if str(channel_id) in db_channels:
            return await query.message.edit_text(f"**✗ ᴄʜᴀɴɴᴇʟ `{channel_id}` ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ ᴀs ᴀ ᴅʙ ᴄʜᴀɴɴᴇʟ!**", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ‹ ʙᴀᴄᴋ', 'db_channels')]]))
        
        # Verify bot can access the channel
        try:
            chat = await client.get_chat(channel_id)
            test_msg = await client.send_message(chat_id=channel_id, text="ᴛᴇsᴛɪɴɢ ᴅʙ ᴄʜᴀɴɴᴇʟ")
            await test_msg.delete()
            
            # Add channel to database
            channel_data = {
                'name': chat.title,
                'is_primary': len(db_channels) == 0,  # First channel becomes primary
                'is_active': True,
                'added_by': query.from_user.id
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
            
            await query.message.edit_text(f"""**✓ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**

›› **ᴄʜᴀɴɴᴇʟ:** `{chat.title}`
›› **ɪᴅ:** `{channel_id}`
›› **sᴛᴀᴛᴜs:** {'ᴘʀɪᴍᴀʀʏ' if channel_data['is_primary'] else 'sᴇᴄᴏɴᴅᴀʀʏ'}""", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ‹ ʙᴀᴄᴋ', 'db_channels')]]))
        
        except Exception as e:
            await query.message.edit_text(f"""**✗ ᴇʀʀᴏʀ ᴀᴄᴄᴇssɪɴɢ ᴄʜᴀɴɴᴇʟ!**

›› **ᴇʀʀᴏʀ:** `{str(e)}`

**ᴘʟᴇᴀsᴇ ᴍᴀᴋᴇ sᴜʀᴇ:**
• ʙᴏᴛ ɪs ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ
• ᴄʜᴀɴɴᴇʟ ɪᴅ ɪs ᴄᴏʀʀᴇᴄᴛ
• ᴄʜᴀɴɴᴇʟ ᴇxɪsᴛs""", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ‹ ʙᴀᴄᴋ', 'db_channels')]]))
    
    except Exception as e:
        await query.message.edit_text(f"""**✗ ᴛɪᴍᴇᴏᴜᴛ ᴏʀ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!**

›› **ᴇʀʀᴏʀ:** `{str(e)}`""", 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ‹ ʙᴀᴄᴋ', 'db_channels')]]))

#===============================================================#

@Client.on_callback_query(filters.regex("^rm_db_channel$"))
async def rm_db_channel(client, query):
    if not query.from_user.id in client.admins:
        return await query.answer('❌ ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs!', show_alert=True)
    
    await query.answer()
    db_channels = getattr(client, 'db_channels', {})
    
    if not db_channels:
        return await query.message.edit_text("**❌ No database channels to remove!**", 
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
    
    msg = f"""<blockquote>**Remove Database Channel:**</blockquote>
**Available Channels:**
"""
    
    for channel_id_str, channel_data in db_channels.items():
        channel_name = channel_data.get('name', 'Unknown')
        is_primary = " (Primary)" if channel_data.get('is_primary', False) else ""
        msg += f"• `{channel_name}` - `{channel_id_str}`{is_primary}\n"
    
    msg += "\n__Send the channel ID you want to remove in the next 60 seconds!__"
    
    await query.message.edit_text(msg)
    try:
        res = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        channel_id_text = res.text.strip()
        
        if not channel_id_text.lstrip('-').isdigit():
            return await query.message.edit_text("**❌ Invalid channel ID!**", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
        
        channel_id = int(channel_id_text)
        
        if str(channel_id) not in db_channels:
            return await query.message.edit_text(f"**❌ Channel `{channel_id}` is not in the DB channels list!**", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
        
        # Check if trying to remove primary channel
        if db_channels[str(channel_id)].get('is_primary', False) and len(db_channels) > 1:
            return await query.message.edit_text("**❌ Cannot remove primary channel!**\n\n__Please set another channel as primary first.__", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
        
        # Remove from database and client
        channel_name = db_channels[str(channel_id)].get('name', 'Unknown')
        await client.mongodb.remove_db_channel(channel_id)
        del client.db_channels[str(channel_id)]
        
        await query.message.edit_text(f"**✅ Database channel removed successfully!**\n\n**Removed:** `{channel_name}` (`{channel_id}`)", 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
    
    except Exception as e:
        await query.message.edit_text(f"**❌ Timeout or error occurred!**\n\n**Error:** `{str(e)}`", 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))

#===============================================================#

@Client.on_callback_query(filters.regex("^set_primary_db$"))
async def set_primary_db(client, query):
    if not query.from_user.id in client.admins:
        return await query.answer('❌ ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs!', show_alert=True)
    
    await query.answer()
    db_channels = getattr(client, 'db_channels', {})
    
    if not db_channels:
        return await query.message.edit_text("**❌ No database channels available!**", 
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
    
    msg = f"""<blockquote>**Set Primary Database Channel:**</blockquote>
**Available Channels:**
"""
    
    for channel_id_str, channel_data in db_channels.items():
        channel_name = channel_data.get('name', 'Unknown')
        is_primary = " (Current Primary)" if channel_data.get('is_primary', False) else ""
        msg += f"• `{channel_name}` - `{channel_id_str}`{is_primary}\n"
    
    msg += "\n__Send the channel ID you want to set as primary in the next 60 seconds!__"
    
    await query.message.edit_text(msg)
    try:
        res = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        channel_id_text = res.text.strip()
        
        if not channel_id_text.lstrip('-').isdigit():
            return await query.message.edit_text("**❌ Invalid channel ID!**", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
        
        channel_id = int(channel_id_text)
        
        if str(channel_id) not in db_channels:
            return await query.message.edit_text(f"**❌ Channel `{channel_id}` is not in the DB channels list!**", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
        
        # Set as primary
        await client.mongodb.set_primary_db_channel(channel_id)
        
        # Update client attributes
        for ch_id, ch_data in client.db_channels.items():
            ch_data['is_primary'] = (int(ch_id) == channel_id)
        
        client.primary_db_channel = channel_id
        client.db = channel_id  # Update current db reference
        
        channel_name = db_channels[str(channel_id)].get('name', 'Unknown')
        await query.message.edit_text(f"**✅ Primary database channel updated!**\n\n**New Primary:** `{channel_name}` (`{channel_id}`)", 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
    
    except Exception as e:
        await query.message.edit_text(f"**❌ Timeout or error occurred!**\n\n**Error:** `{str(e)}`", 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))

#===============================================================#

@Client.on_callback_query(filters.regex("^toggle_db_status$"))
async def toggle_db_status(client, query):
    if not query.from_user.id in client.admins:
        return await query.answer('❌ ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs!', show_alert=True)
    
    await query.answer()
    db_channels = getattr(client, 'db_channels', {})
    
    if not db_channels:
        return await query.message.edit_text("**❌ No database channels available!**", 
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
    
    msg = f"""<blockquote>**Toggle Channel Status:**</blockquote>
**Available Channels:**
"""
    
    for channel_id_str, channel_data in db_channels.items():
        channel_name = channel_data.get('name', 'Unknown')
        status = "🟢 ᴀᴄᴛɪᴠᴇ" if channel_data.get('is_active', True) else "🔴 ɪɴᴀᴄᴛɪᴠᴇ"
        msg += f"• `{channel_name}` - `{channel_id_str}` ({status})\n"
    
    msg += "\n__Send the channel ID you want to ᴀᴄᴛɪᴠᴇ/ɪɴᴀᴄᴛɪᴠᴇ status for in the next 60 seconds!__"
    
    await query.message.edit_text(msg)
    try:
        res = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        channel_id_text = res.text.strip()
        
        if not channel_id_text.lstrip('-').isdigit():
            return await query.message.edit_text("**❌ Invalid channel ID!**", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
        
        channel_id = int(channel_id_text)
        
        if str(channel_id) not in db_channels:
            return await query.message.edit_text(f"**❌ Channel `{channel_id}` is not in the DB channels list!**", 
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
        
        # Toggle status
        new_status = await client.mongodb.toggle_db_channel_status(channel_id)
        
        if new_status is not None:
            # Update client attributes
            client.db_channels[str(channel_id)]['is_active'] = new_status
            
            channel_name = db_channels[str(channel_id)].get('name', 'Unknown')
            status_text = "🟢 Active" if new_status else "🔴 Inactive"
            await query.message.edit_text(f"**✅ Channel status updated!**\n\n**Channel:** `{channel_name}` (`{channel_id}`)\n**New Status:** {status_text}", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
        else:
            await query.message.edit_text("**❌ Failed to toggle channel status!**", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))
    
    except Exception as e:
        await query.message.edit_text(f"**❌ Timeout or error occurred!**\n\n**Error:** `{str(e)}`", 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'db_channels')]]))

#===============================================================#

@Client.on_callback_query(filters.regex("^admins$"))
async def admins(client, query):
    if not (query.from_user.id==OWNER_ID):
        return await query.answer('This can only be used by owner.')
    msg = f"""<blockquote>**Admin Settings:**</blockquote>
**Admin User IDs:** {", ".join(f"`{a}`" for a in client.admins)}

__Use the appropriate button below to add or remove an admin based on your needs!__
"""
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('🟢 ᴀᴅᴅ ᴀᴅᴍɪɴ', 'add_admin'), InlineKeyboardButton('🔴 ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ', 'rm_admin')],
        [InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'settings')]]
    )
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

#===============================================================#

@Client.on_callback_query(filters.regex("^photos$"))
async def photos(client, query):
    msg = f"""<blockquote>**Photo Settings:**</blockquote>
**Start Photo:** `{client.messages.get("START_PHOTO") or "None"}`
**Force Sub Photo:** `{client.messages.get("FSUB_PHOTO") or "None"}`
**Search Photo:** `{client.messages.get("SEARCH_PHOTO") or "None"}`
**Index Photo:** `{client.messages.get("INDEX_PHOTO") or "None"}`

__Set or remove images used by /start, force-sub, anime search, and /anidex.__
"""
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                ("🟢 ꜱᴇᴛ" if not client.messages.get("START_PHOTO") else "🔵 ᴄʜᴀɴɢᴇ") + "\nꜱᴛᴀʀᴛ ᴘʜᴏᴛᴏ",
                callback_data="add_start_photo",
            ),
            InlineKeyboardButton(
                ("🟢 ꜱᴇᴛ" if not client.messages.get("FSUB_PHOTO") else "🔵 ᴄʜᴀɴɢᴇ") + "\nꜰꜱᴜʙ ᴘʜᴏᴛᴏ",
                callback_data="add_fsub_photo",
            ),
        ],
        [
            InlineKeyboardButton(
                ("🟢 ꜱᴇᴛ" if not client.messages.get("SEARCH_PHOTO") else "🔵 ᴄʜᴀɴɢᴇ") + "\nꜱᴇᴀʀᴄʜ ᴘʜᴏᴛᴏ",
                callback_data="add_search_photo",
            ),
            InlineKeyboardButton(
                ("🟢 ꜱᴇᴛ" if not client.messages.get("INDEX_PHOTO") else "🔵 ᴄʜᴀɴɢᴇ") + "\nɪɴᴅᴇx ᴘʜᴏᴛᴏ",
                callback_data="add_index_photo",
            ),
        ],
        [
            InlineKeyboardButton("🔴 ʀᴇᴍᴏᴠᴇ\nꜱᴛᴀʀᴛ ᴘʜᴏᴛᴏ", callback_data="rm_start_photo"),
            InlineKeyboardButton("🔴 ʀᴇᴍᴏᴠᴇ\nꜰꜱᴜʙ ᴘʜᴏᴛᴏ", callback_data="rm_fsub_photo"),
        ],
        [
            InlineKeyboardButton("🔴 ʀᴇᴍᴏᴠᴇ\nꜱᴇᴀʀᴄʜ ᴘʜᴏᴛᴏ", callback_data="rm_search_photo"),
            InlineKeyboardButton("🔴 ʀᴇᴍᴏᴠᴇ\nɪɴᴅᴇx ᴘʜᴏᴛᴏ", callback_data="rm_index_photo"),
        ],
        [InlineKeyboardButton("🔴 ◂ ʙᴀᴄᴋ", callback_data="settings")],
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

#===============================================================#

@Client.on_callback_query(filters.regex("^protect$"))
async def protect(client, query):
    client.protect = False if client.protect else True
    return await settings(client, query)

#===============================================================#

@Client.on_callback_query(filters.regex("^disable_btn$"))
async def disable_btn(client, query):
    client.disable_btn = False if client.disable_btn else True
    return await settings_page_2(client, query)

#===============================================================#

@Client.on_callback_query(filters.regex("^auto_del$"))
async def auto_del(client, query):
    msg = f"""<blockquote>**Change Auto Delete Time:**</blockquote>
**Current Timer:** `{client.auto_del}`

__Enter new integer value of auto delete timer, keep 0 to disable auto delete and -1 to as it was, or wait for 60 second timeout to be comoleted!__
"""
    await query.answer()
    await query.message.edit_text(msg)
    try:
        res = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        timer = res.text.strip()
        if timer.isdigit() or (timer.startswith('+' or '-') and timer[1:].isdigit()):
            timer = int(timer)
            if timer >= 0:
                client.auto_del = timer
                return await query.message.edit_text(f'**Auto Delete timer vakue changed to {timer} seconds!**', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'settings')]]))
            else:
                return await query.message.edit_text("**There is no change done in auto delete timer!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'settings')]]))
        else:
            return await query.message.edit_text("**This is not an integer value!!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'settings')]]))
    except ListenerTimeout:
        return await query.message.edit_text("**Timeout, try again!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'settings')]]))

#===============================================================#

@Client.on_callback_query(filters.regex("^texts$"))
async def texts(client, query):
    msg = f"""<blockquote>**Text Configuration:**</blockquote>
**Start Message:**
<pre>{client.messages.get('START', 'Empty')}</pre>
**Force Sub Message:**
<pre>{client.messages.get('FSUB', 'Empty')}</pre>
**About Message:**
<pre>{client.messages.get('ABOUT', 'Empty')}</pre>
**Index Message (/anidex):**
<pre>{client.messages.get('INDEX', 'Empty')}</pre>
**Reply Message:**
<pre>{client.reply_text}</pre>
    """
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔵 ꜱᴛᴀʀᴛ ᴛᴇxᴛ", "start_txt"), InlineKeyboardButton("🔵 ꜰꜱᴜʙ ᴛᴇxᴛ", "fsub_txt")],
        [InlineKeyboardButton("🔵 ʀᴇᴘʟʏ ᴛᴇxᴛ", "reply_txt"), InlineKeyboardButton("🔵 ᴀʙᴏᴜᴛ ᴛᴇxᴛ", "about_txt")],
        [InlineKeyboardButton("🔵 ɪɴᴅᴇx ᴛᴇxᴛ", "index_txt")],
        [InlineKeyboardButton("🔴 ◂ ʙᴀᴄᴋ", "settings")],
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

#===============================================================#

@Client.on_callback_query(filters.regex('^rm_start_photo$'))
async def rm_start_photo(client, query):
    client.messages['START_PHOTO'] = ''
    await query.answer()
    await photos(client, query)

#===============================================================#

@Client.on_callback_query(filters.regex('^rm_fsub_photo$'))
async def rm_fsub_photo(client, query):
    client.messages['FSUB_PHOTO'] = ''
    await query.answer()
    await photos(client, query)

#===============================================================#

@Client.on_callback_query(filters.regex("^add_start_photo$"))
async def add_start_photo(client, query):
    msg = f"""<blockquote>**Change Start Image:**</blockquote>
**Current Start Image:** `{client.messages.get('START_PHOTO', '')}`

__Enter new link of start image or send the photo, or wait for 60 second timeout to be comoleted!__
"""
    await query.answer()
    await query.message.edit_text(msg)
    try:
        res = await client.listen(user_id=query.from_user.id, filters=(filters.text|filters.photo), timeout=60)
        if res.text and res.text.startswith('https://' or 'http://'):
            client.messages['START_PHOTO'] = res.text
            return await query.message.edit_text("**This link has been set at the place of start photo!!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'photos')]]))
        elif res.photo:
            loc = await res.download()
            client.messages['START_PHOTO'] = loc
            return await query.message.edit_text("**This image has been set as the starting image!!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'photos')]]))
        else:
            return await query.message.edit_text("**Invalid Photo or Link format!!**\n__If you're sending the link of any image it must starts with either 'http' or 'https'!__", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'photos')]]))
    except ListenerTimeout:
        return await query.message.edit_text("**Timeout, try again!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'photos')]]))

#===============================================================#

@Client.on_callback_query(filters.regex("^add_fsub_photo$"))
async def add_fsub_photo(client, query):
    msg = f"""<blockquote>**Change Force Sub Image:**</blockquote>
**Current Force Sub Image:** `{client.messages.get('FSUB_PHOTO', '')}`

__Enter new link of fsub image or send the photo, or wait for 60 second timeout to be comoleted!__
"""
    await query.answer()
    await query.message.edit_text(msg)
    try:
        res = await client.listen(user_id=query.from_user.id, filters=(filters.text|filters.photo), timeout=60)
        if res.text and res.text.startswith('https://' or 'http://'):
            client.messages['FSUB_PHOTO'] = res.text
            return await query.message.edit_text("**This link has been set at the place of fsub photo!!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'photos')]]))
        elif res.photo:
            loc = await res.download()
            client.messages['FSUB_PHOTO'] = loc
            return await query.message.edit_text("**This image has been set as the force sub image!!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'photos')]]))
        else:
            return await query.message.edit_text("**Invalid Photo or Link format!!**\n__If you're sending the link of any image it must starts with either 'http' or 'https'!__", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'photos')]]))
    except ListenerTimeout:
        return await query.message.edit_text("**Timeout, try again!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔴 ◂ ʙᴀᴄᴋ', 'photos')]]))
