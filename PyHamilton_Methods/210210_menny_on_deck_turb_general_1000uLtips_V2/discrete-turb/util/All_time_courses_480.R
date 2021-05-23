
library(RSQLite)
library(dplyr)
library(ggplot2)
library(rstudioapi)
library(data.table)
library(stringr)
library(chron)
library(zoo)
library(sendmailR)

## Get working directory of current file # comment out when running in terminal
current_working_dir <- dirname(rstudioapi::getActiveDocumentContext()$path)
setwd(current_working_dir)


all_data_save = fread("all_time_courses_all_possible_numbers_of_wells_up_to_480.csv")
# only keep by column
class(all_data$num_turbs)

all_data = all_data_save %>% filter(num_turbs  %in% c((1:60)*8))

turbs = data.frame(num_turbs = unique(all_data$num_turbs),
                   col = rep(1:12,5),
                   plate = sort(rep(1:5,12)))

all_data = merge(all_data, turbs)
all_data$actual_k = round(all_data$actual_k, digits = 2)

# all_data  = all_data %>% filter(actual_k > 0.2,
#                                 actual_k < 0.8)

# only keep ones that are a full plate
all_data  =  all_data %>% filter(num_turbs %in% c((1:5)*96))

plotall = ggplot(data = all_data,
                 aes(x = hours, y = od_measurement, color = actual_k, fill = factor(turb_num))) +
  geom_line(alpha = 0.7) + 
  scale_colour_gradientn(colours = rainbow(11))+
  facet_wrap(.~plate, scales = "free") +
  theme_classic()


png(paste0("Figures/", Sys.Date()," all_data.png"), height = 1000, width = 1600)
print(plotall)
dev.off()


pdf(paste0("Figures/", Sys.Date()," all_data.pdf"), height = 5, width = 8)
print(plotall)
dev.off()


unique(all_data$turb_num)



exporting
# growth rate v number of plates ------------------------------------------
all_data = all_data_save %>% filter(num_turbs  %in% c((1:60)*8))

turbs = data.frame(num_turbs = unique(all_data$num_turbs),
                   col = rep(1:12,5),
                   plate = sort(rep(1:5,12)))

all_data = merge(all_data, turbs)
all_data$actual_k = round(all_data$actual_k, digits = 2)

growth = all_data %>% data.frame() %>% dplyr::group_by(turb_num, num_turbs) %>% filter(hours == max(hours))  %>%
  filter(od_measurement > 0.3, od_measurement <  0.5) %>%
  data.frame() %>% group_by(num_turbs) %>%
  filter(actual_k == max(actual_k)) %>% data.frame() %>% 
  group_by(num_turbs) %>% summarise(actual_k = mean(actual_k))

growhtplot = ggplot(data = growth %>% filter(num_turbs > 200),
                 aes(x = num_turbs, y = actual_k)) +
  geom_point() +
  geom_smooth()+
  theme_classic()

pdf(paste0("Figures/", Sys.Date()," num_tubs.pdf"), height = 5, width = 7)
print(growhtplot)
dev.off()


transfer = all_data %>% data.frame() %>% dplyr::group_by(turb_num, num_turbs) %>% filter(hours == max(hours))  %>%
  filter(od_measurement > 0.3, od_measurement <  0.5) %>%
  data.frame() %>% group_by(plate, actual_k) %>%
  filter(transfer_vol == max(transfer_vol)) %>% data.frame() %>% 
  group_by(actual_k, plate) %>% summarise(transfer_vol = mean(transfer_vol))


transfer_plot = ggplot(data = transfer %>% data.frame() %>% filter(transfer_vol < 0.6),
                    aes(x = actual_k, y = transfer_vol, color = factor(plate), fill = factor(plate))) +
  geom_point() +
  geom_smooth(method = lm, se = FALSE) +
  theme_classic()

pdf(paste0("Figures/", Sys.Date()," transfervol.pdf"), height = 5, width = 7)
print(transfer_plot)
dev.off()




                 
                