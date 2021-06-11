import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, CDSView, GroupFilter, Paragraph, HoverTool, Span, Label
from bokeh.plotting import figure


# Set up data
df = pd.read_csv('submissions.csv')
df_new = pd.DataFrame()
for name in df['name'].unique():
    sub_df = df.loc[df['name']==name]
    sub_df = sub_df.sort_values("days_from_start").reset_index(drop=True)
    sub_df['auc_max']=sub_df['auc'].cummax()
    df_new = pd.concat([df_new, sub_df])
df = df_new.copy()
df['day_round'] = np.floor(df["days_from_start"]).astype(int)

# Day counts for daily submissions
day_rounds = df.groupby(['day_round']).size().reset_index()
day_rounds.columns = ['day', 'count']
cds_day_hist = ColumnDataSource(day_rounds)

# Color participants by score
auc_grp = df.groupby('name').agg({'auc_max':'max'}).reset_index()
auc_grp = auc_grp.sort_values('auc_max', ascending=False)
name_list = list(auc_grp["name"])
color_list = ["#AD57C5","#E13C2B", "#0075F6"]+["#b8b2b2"]*len(name_list)
color_list = color_list[:len(name_list)]
col_df = pd.DataFrame({'name': name_list, 'color': color_list})

df=df.merge(col_df, on='name', how='left')
cds = ColumnDataSource(df)

# Set up leaderboard
p = figure(plot_width=600, plot_height=400,
           title="Best scores on Kaggle public leaderboard in time",
           tools="pan,tap,wheel_zoom,reset",
           x_axis_label="Days from challenge start",
           y_axis_label='AUC score', x_range=(-1, 53), y_range=(0.775, round(df['auc'].max(), 2)))

p.circle(x='days_from_start', y='auc_max', source=cds, size=3, legend_field='name', fill_color='color', line_color='color')

winner_num=0 # Visualise winners differently
for name, mycolor in zip(list(col_df["name"]), list(col_df['color'])):
    my_line_width=2
    my_alpha=0.6
    if winner_num<3:
        my_line_width=3
        my_alpha=0.8
    winner_num+=1
    myview = CDSView(source=cds, filters=[GroupFilter(column_name='name', group=name)])
    p.step(x='days_from_start', y='auc_max', line_width=my_line_width, source=cds, view=myview, line_alpha=my_alpha, legend_field='name', line_color=mycolor, mode="after")

p.legend.visible=False
p.title.text_font_size = '12pt'
p.xaxis.axis_label_text_font_size = "10pt"
p.yaxis.axis_label_text_font_size = "10pt"
p.yaxis.axis_label_text_font_size = "10pt"
p.xaxis.axis_label_text_font_size = "10pt"
p.xgrid.grid_line_color = None
p.ygrid.grid_line_color = None
p.toolbar_location = None

# Add baseline
baseline=0.78694
horizontal_line = Span(location=baseline, dimension='width', line_color='red', line_width=2, line_alpha=0.6)
horizontal_line_label = Label(text="baseline", text_color="red", x=40, y=horizontal_line.location)
p.renderers.extend([horizontal_line, horizontal_line_label])

# Add hover tool
scatter_hover = HoverTool(tooltips = [("Name", "@name"), ("AUC", "@auc_max"), ("Day", "@days_from_start")])
p.tools.append(scatter_hover)

# Daily submission histogram
p_hist = figure(width = 300, height=210, title="Daily submissions",
                toolbar_location=None, tools="",
                x_axis_label="Days from start") # x_range=(-1, 53)
p_hist.vbar(x='day', top='count', width=0.8, source=cds_day_hist, hover_color="#900C3E", color="#FC4237")
p_hist.xgrid.grid_line_color = None
hist_hover = HoverTool(tooltips = [("Day", "@day"), ("Submissions", "@count")])
p_hist.tools.append(hist_hover)
p_hist.title.text_font_size = '12pt'
p_hist.xaxis.axis_label_text_font_size = "10pt"


# Define widgets
days_from_start = Slider(title="Days from challenge start", value=1, start=0, end=df['day_round'].max(), step=1) # 53
auc_threshold = Slider(title="Filter participants (above AUC)", value=baseline, start=round(df['auc'].mean(), 2), end=round(df['auc'].max(), 2), step=0.001, format='0.00f')

winners = df.groupby('name').agg({'auc_max':'max', 'color':'max'}).reset_index().sort_values('auc_max', ascending=False).reset_index(drop=True).head(3)
winner_text = "{place}: {name} with {score}"
winner_1 = Paragraph(text=winner_text.format(place='1st', name=winners.loc[0,"name"], score=str(round(winners.loc[0,"auc_max"],3))), background=winners.loc[0,"color"], style={'color': '#FFFFFF'})
winner_2 = Paragraph(text=winner_text.format(place='2nd', name=winners.loc[1,"name"], score=str(round(winners.loc[1,"auc_max"],3))), background=winners.loc[1,"color"], style={'color': '#FFFFFF'})
winner_3 = Paragraph(text=winner_text.format(place='3rd', name=winners.loc[2,"name"], score=str(round(winners.loc[2,"auc_max"],3))), background=winners.loc[2,"color"], style={'color': '#FFFFFF'})


# Set up callbacks
def update_cds(days_threshold, auc_threshold):
    name_grp = auc_grp.loc[auc_grp['auc_max']>auc_threshold]
    df_filtered = df[df['days_from_start']<=days_threshold].copy()
    df_filtered = df_filtered.loc[df_filtered['name'].isin(list(name_grp['name']))]
    day_rounds = df_filtered.groupby(['day_round']).size().reset_index()
    day_rounds.columns = ['day', 'count']

    cds.data = df_filtered
    cds_day_hist.data = day_rounds
    return df_filtered

def update_data(attrname, old, new):
    b = days_from_start.value # current slider values
    c = auc_threshold.value

    df_filtered = update_cds(b, c)
    if len(df_filtered)>0:
        winners = df_filtered.groupby('name').agg({'auc_max':'max', 'color':'max'}).reset_index().sort_values('auc_max', ascending=False).reset_index(drop=True).head(3)
        winner_1.text = winner_text.format(place='1st', name=winners.loc[0,"name"], score=str(round(winners.loc[0,"auc_max"],3)))
        winner_1.background = winners.loc[0,"color"]
        if len(winners)>1:
            winner_2.text = winner_text.format(place='2nd', name=winners.loc[1,"name"], score=str(round(winners.loc[1,"auc_max"],3)))
            winner_2.background = winners.loc[1,"color"]
        if len(winners)>2:
            winner_3.text = winner_text.format(place='3rd', name=winners.loc[2,"name"], score=str(round(winners.loc[2,"auc_max"],3)))
            winner_3.background = winners.loc[2,"color"]
    else:
        winner_1.text = 'No winner'
        winner_2.text = 'No winner'
        winner_3.text = 'No winner'

for w in [days_from_start, auc_threshold]:
    w.on_change('value', update_data)

# Initial filter
_ = update_cds(days_from_start.value, auc_threshold.value)


# Layout
inputs = column(days_from_start, auc_threshold, winner_1, winner_2, winner_3, p_hist)

curdoc().add_root(row(p, inputs, width=1800))
curdoc().title = "Leaderboard"