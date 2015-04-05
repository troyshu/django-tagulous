"""
Tag parsing and printing

Loosely based on django-taggit and django-tagging
"""
from collections import deque

from django.conf import settings as global_settings
from django.utils.encoding import force_unicode
from django.utils.functional import wraps

from tagulous import settings

# Constants to improve legibility
COMMA = u','
SPACE = u' '
QUOTE = u'"'


def parse_tags(tag_string, max_count=0):
    """
    Tag parser
    
    Rules without quotes:
        If a comma is present it's used as the delimiter
        Otherwise space is used as the delimiter
        Spaces at the start and end of tags are ignored
    
    Rules with quotes
        Quotes can be escaped by double quotes, eg ""
        All unescaped quotes are checked to see if they're followed by 
    
        First space or comma after a quote 
        If a tag starts with a quote
    """
    # Empty string easiest case
    if not tag_string:
        return []
    
    tag_string = force_unicode(tag_string)
    
    # Prep variables for the parser
    tags = []
    tag = ''
    delimiter = SPACE
    in_quote = None
    chars = False
    
    # Bypass main parser if no quotes - simple split and strip
    if QUOTE not in tag_string:
        # Normally split on commas
        delimiter = COMMA
        
        # But if no commas, split on spaces
        if COMMA not in tag_string:
            delimiter = SPACE
        
        # Return sorted list of unique stripped tags
        tags = list(set(split_strip(tag_string, delimiter)))
        tags.sort()
        
    else:
        # Break tag string into list of (index, char)
        chars = list(enumerate(tag_string))
    
    # Loop through chars
    while chars:
        index, char = chars.pop(0)
        
        # See if it's a delimiter
        if not in_quote:
            # Comma delimiter takes priority
            if delimiter != COMMA and char == COMMA:
                delimiter = COMMA
                
                # All previous tags were actually just one tag
                tag = tag_string[0:index].strip()
                tags = []
                
                # Escape quotes
                tag_len = len(tag)
                tag = tag.lstrip(QUOTE)
                left_quote_count = tag_len - len(tag)
                tag = QUOTE * (left_quote_count / 2) + tag
                
                tag_len = len(tag)
                tag = tag.rstrip(QUOTE)
                right_quote_count = tag_len - len(tag)
                tag = QUOTE * (right_quote_count / 2) + tag
                
                # Add back insignificant unquoted quotes
                if left_quote_count % 2 == 1:
                    if right_quote_count % 2 != 1:
                        tag = QUOTE + tag
                elif right_quote_count % 2 == 1:
                    tag += QUOTE
                
            
            # Found end of tag
            if char == delimiter:
                tags.append(tag.rstrip())
                tag = ''
                continue
                
            # If tag is empty, ignore whitespace
            if not tag and char == SPACE:
                continue
            
        # Now either in a quote, or not a delimiter
        # If it's not a quote, add to tag
        if char != QUOTE:
            tag += char
            continue
        
        # Char is quote - count how many quotes appear here
        quote_count = 1
        while chars and chars[0][1] == QUOTE:
            quote_count += 1
            chars.pop(0)
        
        if not tag:
            # Quote at start
            # If an odd number, now in quote
            if quote_count % 2 == 1:
                in_quote = True
            
            # Tag starts with escaped quotes
            tag = QUOTE * (quote_count / 2)
        else:
            # Quote in middle or at end
            # Add any escaped
            tag += QUOTE * (quote_count / 2)
            
            # An odd number followed by a delimiter will mean it has ended
            # Need to look ahead to figure it out
            if quote_count % 2 == 1:
                
                # If it's the last character, it has closed
                if len(chars) == 0:
                    in_quote = False
                    break;
                
                for i2, c2 in chars:
                    if c2 == SPACE:
                        if delimiter == SPACE:
                            # Quotes closed; tag will end next loop
                            in_quote = False
                            break
                        else:
                            # Spaces are insignificant during whitespace
                            # Tag may continue, keep checking chars
                            continue
                    elif c2 == COMMA:
                        # Quotes closed; tag will end next loop
                        # Delimiter doesn't matter, comma always wins
                        in_quote = False
                        break
                    
                    # Tag has not ended
                    # Add odd quote to tag and keep building
                    tag += QUOTE
                    break
    
    # Chars expended
    if tag:
        # Partial tag remains; add to stack
        if in_quote:
            # Add the quote back to the start - it wasn't significant after all
            tag = QUOTE + tag
        tags.append(tag)
    
    # Check the count
    if max_count and len(tags) > max_count:
        raise ValueError('This field can only have %s argument%s'
            % (max_count, '' if max_count == 1 else 's')
        )
    
    return tags
    
    
def split_strip(string, delimiter=u','):
    """
    Splits ``string`` on ``delimiter``, stripping each resulting string
    and returning a list of non-empty strings.
    """
    if not string:
        return []

    words = [w.strip() for w in string.split(delimiter)]
    return [w for w in words if w]


def render_tags(tags):
    """
    Creates a tag string from a list of Tag instances or strings, suitable for
    editing.

    Tag names which contain commas will be quoted, existing quotes will be
    escaped.
    """
    names = []
    for tag in tags:
        # This will catch a list of Tag objects or tag name strings
        name = u'%s' % tag
        name = name.replace(QUOTE, QUOTE + QUOTE)
        if COMMA in name or SPACE in name:
            names.append(u'"%s"' % name)
        else:
            names.append(name)
    return u', '.join(sorted(names))


def get_setting(setting):
    """
    Helper function to get a setting from global settings, or tagulous defaults
    """
    if hasattr(global_settings, setting):
        return getattr(global_settings, setting)
    if hasattr(settings, setting):
        return getattr(settings, setting)
    raise ValueError("Invalid setting %s" % setting)
    