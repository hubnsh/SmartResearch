/* Inline Markdown Parser - zero dependencies */
var marked = { parse: function(t) {
    if (!t) return '';
    t = t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

    // Fenced code blocks
    t = t.replace(/```(\w*)\r?\n([\s\S]*?)```/g, function(_,lang,code){
        return '<pre><code>' + code.replace(/</g,'&lt;').trim() + '</code></pre>';
    });

    // Inline code
    t = t.replace(/`([^`]+)`/g,'<code>$1</code>');

    // Headers
    t = t.replace(/^#### (.+)$/gm,'<h4>$1</h4>');
    t = t.replace(/^### (.+)$/gm,'<h3>$1</h3>');
    t = t.replace(/^## (.+)$/gm,'<h2>$1</h2>');
    t = t.replace(/^# (.+)$/gm,'<h1>$1</h1>');

    // Bold / Italic
    t = t.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
    t = t.replace(/\*(.+?)\*/g,'<em>$1</em>');

    // Links & Images
    t = t.replace(/!\[(.+?)\]\((.+?)\)/g,'<img src="$2" alt="$1">');
    t = t.replace(/\[(.+?)\]\((.+?)\)/g,'<a href="$2" target="_blank">$1</a>');

    // Tables
    t = t.replace(/((?:^\|.+\|\r?\n)+)/gm, function(block){
        var rows = block.trim().split(/\r?\n/).filter(function(r){
            return r.indexOf('|') !== -1 && r.indexOf('---') === -1;
        });
        if (rows.length < 2) return block;
        var h = '<table>';
        rows.forEach(function(row,i){
            var cells = row.split('|').filter(function(c){ return c.trim(); });
            var tag = i === 0 ? 'th' : 'td';
            h += '<tr>' + cells.map(function(c){ return '<'+tag+'>'+c.trim()+'</'+tag+'>'; }).join('') + '</tr>';
        });
        return h + '</table>';
    });

    // Unordered lists
    t = t.replace(/((?:^[-*] .+\r?\n?)+)/gm, function(m){
        return '<ul>' + m.replace(/^[-*] (.+)/gm,'<li>$1</li>') + '</ul>';
    });
    // Ordered lists
    t = t.replace(/((?:^\d+\. .+\r?\n?)+)/gm, function(m){
        return '<ol>' + m.replace(/^\d+\. (.+)/gm,'<li>$1</li>') + '</ol>';
    });

    // Blockquote & hr
    t = t.replace(/^> (.+)$/gm,'<blockquote>$1</blockquote>');
    t = t.replace(/^(---|\*\*\*)$/gm,'<hr>');

    // Paragraphs & line breaks
    t = t.replace(/\n\n/g,'</p><p>');
    t = t.replace(/\n/g,'<br>');

    return '<p>' + t + '</p>';
}};
