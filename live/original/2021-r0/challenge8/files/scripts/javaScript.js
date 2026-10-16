function openLink(url) {
    window.open(url, '_blank');
}

function selection() {
    var f = document.getElementById('SELECT');
    var selectedValue = f.options[f.selectedIndex].value;
    
    switch (selectedValue) {
        case '0': openLink('https://nzcsc.org.nz/'); break;
        case '1': openLink('https://nzcsc.org.nz/challenge1/'); break;
        case '2': openLink('https://nzcsc.org.nz/challenge2/'); break;
        case '3': openLink('https://nzcsc.org.nz/challenge3/'); break;
        case '4': openLink('https://nzcsc.org.nz/challenge4/'); break;
        case '5': openLink('https://nzcsc.org.nz/challenge5/'); break;
        case '6': openLink('https://nzcsc.org.nz/challenge6/'); break;
        case '7': openLink('https://nzcsc.org.nz/challenge7/'); break;
        case '8': openLink('https://nzcsc.org.nz/challenge8/'); break;
        case '9': openLink('https://nzcsc.org.nz/challenge9/'); break;
        case '10': openLink('https://nzcsc.org.nz/challenge10/'); break;
        case '11': openLink('https://nzcsc.org.nz/challenge11/'); break;
        case '12': openLink('https://nzcsc.org.nz/challenge12/'); break;
        default: openLink('https://nzcsc.org.nz'); break;
    }
    
}