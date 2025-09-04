# Scanned PDFs Requiring OCR Processing

Generated: 2025-08-27

## Summary
- **Total PDFs analyzed:** 108 files
- **Searchable (native text):** 98 files (90.7%)
- **Scanned (needs OCR):** 10 files (9.3%)

## Scanned PDF Files
These PDFs are image-only and require OCR processing to extract text:

### Full Paths
```
data/Stoneman_dispute/user_data/UD - Complaint Summons, POS (full).pdf
data/Stoneman_dispute/user_data/UD - 60 Day Notice Request to Post and Mail 4-15-2025_4.pdf
data/Stoneman_dispute/user_data/Animal Addendum 09.04.2024.pdf
data/Stoneman_dispute/user_data/Doc - Hoa Laws.pdf
data/Stoneman_dispute/user_data/60 Day Notice To Quit (Official) 1:29:25.pdf
data/Stoneman_dispute/user_data/Civil - Family Move - Robert L.pdf
data/Stoneman_dispute/user_data/StonemanCourt-CC&R.pdf
data/Stoneman_dispute/user_data/3 Day Notice - 07:14:25.pdf
data/Stoneman_dispute/user_data/Notice to repair 08182025.pdf
data/Stoneman_dispute/user_data/60 day notice 06:19:2025.pdf
```

### File Names Only
1. `UD - Complaint Summons, POS (full).pdf`
2. `UD - 60 Day Notice Request to Post and Mail 4-15-2025_4.pdf`
3. `Animal Addendum 09.04.2024.pdf`
4. `Doc - Hoa Laws.pdf`
5. `60 Day Notice To Quit (Official) 1:29:25.pdf`
6. `Civil - Family Move - Robert L.pdf`
7. `StonemanCourt-CC&R.pdf`
8. `3 Day Notice - 07:14:25.pdf`
9. `Notice to repair 08182025.pdf`
10. `60 day notice 06:19:2025.pdf`

## Processing Command
To process these scanned PDFs with OCR:
```bash
# Process all scanned PDFs
for pdf in "data/Stoneman_dispute/user_data/UD - Complaint Summons, POS (full).pdf" \
           "data/Stoneman_dispute/user_data/UD - 60 Day Notice Request to Post and Mail 4-15-2025_4.pdf" \
           "data/Stoneman_dispute/user_data/Animal Addendum 09.04.2024.pdf" \
           "data/Stoneman_dispute/user_data/Doc - Hoa Laws.pdf" \
           "data/Stoneman_dispute/user_data/60 Day Notice To Quit (Official) 1:29:25.pdf" \
           "data/Stoneman_dispute/user_data/Civil - Family Move - Robert L.pdf" \
           "data/Stoneman_dispute/user_data/StonemanCourt-CC&R.pdf" \
           "data/Stoneman_dispute/user_data/3 Day Notice - 07:14:25.pdf" \
           "data/Stoneman_dispute/user_data/Notice to repair 08182025.pdf" \
           "data/Stoneman_dispute/user_data/60 day notice 06:19:2025.pdf"; do
    tools/scripts/vsearch upload "$pdf"
done
```

Or using the vsearch tool individually:
```bash
tools/scripts/vsearch upload "data/Stoneman_dispute/user_data/UD - Complaint Summons, POS (full).pdf"
```