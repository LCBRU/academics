from academics.model.publication import NihrAcknowledgement

def is_match(text, expected):
    assert NihrAcknowledgement.get_strict_match(text) == expected
    assert NihrAcknowledgement.get_strict_match('Some prior Text. ' + text) == expected
    assert NihrAcknowledgement.get_strict_match(text + ' Some post text') == expected
    assert NihrAcknowledgement.get_strict_match('Some prior Text. ' + text + ' Some post text') == expected


assert NihrAcknowledgement.get_strict_match('Hello') == None

for sr in ['study', 'research']:
    text = f'This {sr} is funded by the National Institute for Health and Care Research (NIHR) Leicester Biomedical Research Centre. The views expressed are those of the author(s) and not necessarily those of the NIHR or the Department of Health and Social Care'
    is_match(text, 1)

is_match('This study has been delivered through the National Institute for Health and Care Research (NIHR) Leicester Biomedical Research Centre. The views expressed are those of the author(s) and not necessarily those of the Yo Mom\'s Research Fund, the NIHR or the Department of Health and Social Care', 2)
is_match('The research was carried out at the National Institute for Health and Care Research (NIHR) Leicester Biomedical Research Centre', 3)

