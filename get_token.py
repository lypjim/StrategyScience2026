#!/usr/bin/env python3
"""
Extract the Dropbox token from user's message using direct line extraction.
"""

def extract_token_from_message():
    """Extract token by finding the line containing the token."""
    # Your message as provided
    your_message = '''sl.u.AGSDEemh3KB4DXlC7aKYzy6rVbTje1sTKJGeZC1VYEmk2GaecHP0G63x2TuSuiUz26MujHm1P0sPe-vZr42IPDibHMtmyDXrcN0JOhpUzhZ_6Lc7IRMwtmpSMzRqL-bErZqnDv640dtr-p5Jo1buRLeczQTpgD3IwFstKJLwFLU3MSkmZc_uqcj8-dKdwN0Qp7WJ10p4wumbNMbK7impXaxIRHa6j54ogRWt_3TegyMfiwywWxitvwkNts_5RPWpMgr0lXFPj_mS12RQqhQ5P7PMucs22UF5B7Zx0AhB2_OAPyO0jkLnpxfPBmOiEKZJ058KYlo2qLGiQdtzafwrr_TveH8jKyYCCJ3OVDP2RmRophJLiFB8NWet14Rv6XWQtsb7zlqxJqSfCryfukNvJ0PP-3wHUosaD9m1FhclLrEL_f-IhS_NEkkrORgNPKqONurGYvFsmqRRLJIsUFja3OYQKPA7zuTNChgq-3OjZS-du115PVGZ1wonCua4Aq2oEasUdPPDGEB5wS6EnQUdtdpo5mV8ty8l2FTi24nymkUfU1MkgEaTh3jXJtbqf6wrHmo4mODcV7uFcRoAaqXk_ljrfUCxATLQQ2XJHE4DyrEpowMXFf7-TsZbmCm8fHuvT15SD78OgFxTMtGdT5AXEalN_CYD3eBX6KxspO-Oz83np3fELyyfggFW5es6iOs6Hy-MKTfxY-5p5ucFmIn_t1RhRNiniS4OAfZvpj8R6Jl5HUB5GEvQ_ICB6ND91w5fYkfTZwVAG7yrpr1NUponBzlrbMXuKBWhBV-Xj4f4im3n7CPmk0fzdi7YRFB9zMcYnWvjB7K84-gednmJR1skUa_IjRWYBrfbUyjozbkC5dHsMLJxYZQusHc6hD12rOoK4GDNpQmOi_Code
```

def extract_token():
    """Extract the Dropbox token by finding the line starting with 'sl.u.'"""
    lines = your_message.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('sl.u.'):
            # Extract just the token part
            token = line[5:].strip()
            if token and len(token) > 50:  # Basic validation
                print(f"✓ Extracted token: {token[:20]}...")
                return token
    
    print("❌ No token found in message")
    return None

if __name__ == "__main__":
    token = extract_token()
    if token:
        print(f"\n🔑 Extracted Token: {token}")
    else:
        print("\n❌ Could not extract token from message")