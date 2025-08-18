"""
Test HTML cleaning functionality for document export.
"""

from shared.html_cleaner import clean_html_content, extract_email_content
from infrastructure.pipelines.document_exporter import DocumentExporter


class TestHTMLCleaning:
    
    def test_basic_html_cleaning(self):
        """Test basic HTML tag removal and cleaning"""
        html = '<p>Hello <strong>world</strong>!</p><div>New paragraph</div>'
        expected = 'Hello world!\nNew paragraph'
        result = clean_html_content(html)
        assert result == expected
    
    def test_email_style_html_cleaning(self):
        """Test cleaning of complex email HTML with inline styles"""
        html = '''
        <p style="margin:0in;line-height:normal;font-size:12pt;">
        The delivery of a tenancy termination notice is significant.
        </p>
        <div dir="ltr">We are available August 7 as early as 8:30am.</div>
        '''
        result = clean_html_content(html)
        
        # Should remove all HTML and styling
        assert '<' not in result
        assert '>' not in result
        assert 'style=' not in result
        assert 'tenancy termination notice' in result
        assert 'August 7' in result
    
    def test_nested_email_content(self):
        """Test cleaning of nested email blockquotes"""
        html = '''
        <p>Original message here</p>
        <blockquote type="cite">
            <div>On Jul 31, 2025, Jen wrote:</div>
            <p>Previous email content</p>
        </blockquote>
        '''
        result = clean_html_content(html)
        
        assert 'Original message here' in result
        assert 'On Jul 31, 2025' in result
        assert 'Previous email content' in result
        assert '<blockquote' not in result
    
    def test_email_metadata_extraction(self):
        """Test extraction of email metadata from HTML"""
        html = '''
        <div>From: john@example.com</div>
        <div>Subject: Important Update</div>
        <div>Date: Aug 17, 2025</div>
        <p>Email body content here</p>
        '''
        content, metadata = extract_email_content(html)
        
        assert 'john@example.com' in metadata.get('sender', '')
        assert 'Important Update' in metadata.get('subject', '')
        assert 'Aug 17, 2025' in metadata.get('date', '')
        assert 'Email body content' in content
    
    def test_document_exporter_html_cleaning(self):
        """Test that DocumentExporter properly cleans HTML email content"""
        exporter = DocumentExporter()
        
        content_dict = {
            'content_id': 'test-email-123',
            'content_type': 'email',
            'title': 'Test Email with HTML',
            'content': '''
            <p style="margin:0in">Important legal notice</p>
            <div dir="ltr">Meeting scheduled for tomorrow</div>
            <blockquote>Previous email quoted here</blockquote>
            ''',
            'created_time': '2025-08-17T10:00:00',
            'metadata': {}
        }
        
        result = exporter.format_as_markdown(content_dict)
        
        # Should contain cleaned content
        assert 'Important legal notice' in result
        assert 'Meeting scheduled' in result
        
        # Should not contain HTML
        assert '<p style=' not in result
        assert '<div dir=' not in result
        assert '<blockquote>' not in result
        
        # Should have proper markdown structure
        assert '# Test Email with HTML' in result
        assert '## Content' in result
        assert '---' in result  # YAML frontmatter
    
    def test_non_html_content_unchanged(self):
        """Test that non-HTML content passes through unchanged"""
        exporter = DocumentExporter()
        
        content_dict = {
            'content_id': 'test-text-123',
            'content_type': 'text',
            'title': 'Plain Text Document',
            'content': 'This is plain text content with no HTML tags.',
            'created_time': '2025-08-17T10:00:00',
            'metadata': {}
        }
        
        result = exporter.format_as_markdown(content_dict)
        
        # Should contain original content unchanged
        assert 'This is plain text content with no HTML tags.' in result
        assert '# Plain Text Document' in result
    
    def test_list_formatting(self):
        """Test that HTML lists are converted to markdown lists"""
        html = '''
        <ul>
            <li>First item</li>
            <li>Second item</li>
        </ul>
        '''
        result = clean_html_content(html)
        
        assert '• First item' in result
        assert '• Second item' in result
    
    def test_whitespace_normalization(self):
        """Test that excessive whitespace is normalized"""
        html = '''
        <p>    Lots   of   spaces    </p>
        
        
        
        <div>Multiple newlines above</div>
        '''
        result = clean_html_content(html)
        
        # Should normalize spaces and newlines
        assert '    ' not in result
        assert 'Lots of spaces' in result
        assert '\n\n\n' not in result
    
    def test_html_entity_decoding(self):
        """Test that HTML entities are properly decoded"""
        html = '<p>&lt;test&gt; &amp; &quot;example&quot;</p>'
        result = clean_html_content(html)
        
        assert '<test>' in result
        assert '&' in result
        assert '"example"' in result
        assert '&lt;' not in result
        assert '&amp;' not in result
        assert '&quot;' not in result